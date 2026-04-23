/**
 * Account Summary API client
 *
 * Fetches a customer's account balances and recent transaction history
 * from the internal banking API.
 */

// -----------------------------------------------------------------------------
// Domain Types
// -----------------------------------------------------------------------------

/** A single debit or credit transaction on a customer's account. */
export interface Transaction {
  /** Unique transaction identifier (UUID). */
  id: string;
  /** ISO 8601 date string of when the transaction was posted. */
  date: string;
  /** Transaction amount in USD. Negative values indicate debits. */
  amount: number;
  /** Name of the merchant or counterparty. */
  merchant: string;
  /** Whether this is a debit or credit to the account. */
  type: "debit" | "credit";
}

/** Aggregated account balances and recent activity for a customer. */
export interface AccountSummary {
  /** Current available balance in the checking account (USD). */
  checkingBalance: number;
  /** Current available balance in the savings account (USD). */
  savingsBalance: number;
  /** The five most recent transactions across all accounts, newest first. */
  last5Transactions: Transaction[];
}

// -----------------------------------------------------------------------------
// Custom Error Classes
// -----------------------------------------------------------------------------

/** Thrown when the API rejects the request due to an invalid or expired token. */
export class AuthenticationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuthenticationError";
  }
}

/** Thrown when the upstream banking service fails to respond in time. */
export class NetworkTimeoutError extends Error {
  /** Suggested wait time in seconds before the caller retries. */
  readonly retryAfterSeconds: number;

  constructor(message: string, retryAfterSeconds = 30) {
    super(message);
    this.name = "NetworkTimeoutError";
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

/** Thrown for any unexpected non-2xx response not handled by a specific error class. */
export class GeneralApiError extends Error {
  /** HTTP status code returned by the API. */
  readonly statusCode: number;

  constructor(message: string, statusCode: number) {
    super(message);
    this.name = "GeneralApiError";
    this.statusCode = statusCode;
  }
}

// -----------------------------------------------------------------------------
// API Client
// -----------------------------------------------------------------------------

const ACCOUNT_SUMMARY_BASE_URL = "https://api.internalbank.com/accounts";

/**
 * Retrieves the account summary for a given customer.
 *
 * @param customerId - The unique identifier of the customer whose accounts are being queried.
 * @param authToken  - A valid Bearer token obtained from the authentication service.
 * @returns A promise that resolves to the customer's {@link AccountSummary}.
 *
 * @throws {AuthenticationError}   If the server responds with 401 Unauthorized.
 * @throws {NetworkTimeoutError}   If the server responds with 504 Gateway Timeout.
 * @throws {GeneralApiError}       If the server responds with any other non-2xx status.
 *
 * @example
 * const summary = await getAccountSummary("cust_abc123", token);
 * console.log(summary.checkingBalance);
 */
export async function getAccountSummary(
  customerId: string,
  authToken: string
): Promise<AccountSummary> {
  const endpoint = `${ACCOUNT_SUMMARY_BASE_URL}/${customerId}/summary`;

  const response = await fetch(endpoint, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${authToken}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    switch (response.status) {
      case 401:
        throw new AuthenticationError(
          "Access denied: the provided authentication token is invalid or has expired. " +
            "Please re-authenticate and retry."
        );

      case 504:
        throw new NetworkTimeoutError(
          "The banking service did not respond in time. " +
            "Please wait 30 seconds before retrying.",
          30
        );

      default:
        throw new GeneralApiError(
          `Unexpected response from account summary service (HTTP ${response.status}).`,
          response.status
        );
    }
  }

  const data = await response.json() as AccountSummary;

  // An empty transaction list is valid (e.g. a newly opened account).
  // Return the object as-is rather than treating it as an error.
  return {
    checkingBalance:   data.checkingBalance,
    savingsBalance:    data.savingsBalance,
    last5Transactions: data.last5Transactions ?? [],
  };
}
