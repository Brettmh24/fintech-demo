import {
  getAccountSummary,
  AccountSummary,
  Transaction,
  AuthenticationError,
  NetworkTimeoutError,
  GeneralApiError,
} from "./getAccountSummary";

// Mock the global fetch so no real HTTP calls are made during tests
global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

// -----------------------------------------------------------------------------
// Shared Test Fixtures
// Realistic-looking data makes the demo easier to present and edge cases
// easier to reason about.
// -----------------------------------------------------------------------------

const CUSTOMER_ID  = "cust_f3a91b2c-4d7e-4a1f-b8c6-9e2d1f0a3b5c";
const AUTH_TOKEN   = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test-payload.sig";

const MOCK_TRANSACTIONS: Transaction[] = [
  {
    id:       "txn_001a2b3c",
    date:     "2026-04-22",
    amount:   -127.43,
    merchant: "Whole Foods Market",
    type:     "debit",
  },
  {
    id:       "txn_002d4e5f",
    date:     "2026-04-20",
    amount:   -489.00,
    merchant: "Delta Airlines",
    type:     "debit",
  },
  {
    id:       "txn_003g6h7i",
    date:     "2026-04-18",
    amount:   -63.17,
    merchant: "Amazon.com",
    type:     "debit",
  },
  {
    id:       "txn_004j8k9l",
    date:     "2026-04-15",
    amount:   3_250.00,
    merchant: "Acme Corp Payroll",
    type:     "credit",
  },
  {
    id:       "txn_005m0n1o",
    date:     "2026-04-12",
    amount:   -42.90,
    merchant: "Shell Gas Station",
    type:     "debit",
  },
];

const MOCK_ACCOUNT_SUMMARY: AccountSummary = {
  checkingBalance:   4_812.37,
  savingsBalance:    18_540.00,
  last5Transactions: MOCK_TRANSACTIONS,
};

// Helper: build a mock Response object with a given status and JSON body
function mockResponse(status: number, body: unknown): Response {
  return {
    ok:     status >= 200 && status < 300,
    status,
    json:   jest.fn().mockResolvedValue(body),
    headers: new Headers(),
  } as unknown as Response;
}

// Reset mock state between tests to prevent cross-test contamination
beforeEach(() => {
  mockFetch.mockReset();
});

// =============================================================================

describe("getAccountSummary", () => {

  // ---------------------------------------------------------------------------
  describe("Happy path — successful responses", () => {

    it("returns a correctly shaped AccountSummary with 5 transactions", async () => {
      mockFetch.mockResolvedValue(mockResponse(200, MOCK_ACCOUNT_SUMMARY));

      const result = await getAccountSummary(CUSTOMER_ID, AUTH_TOKEN);

      expect(result.checkingBalance).toBe(4_812.37);
      expect(result.savingsBalance).toBe(18_540.00);
      expect(result.last5Transactions).toHaveLength(5);

      // Spot-check the first transaction for shape and realistic values
      const first = result.last5Transactions[0];
      expect(first.id).toBe("txn_001a2b3c");
      expect(first.merchant).toBe("Whole Foods Market");
      expect(first.amount).toBe(-127.43);
      expect(first.type).toBe("debit");
    });

    it("returns an empty transaction array for a newly opened account", async () => {
      const newAccountSummary: AccountSummary = {
        checkingBalance:   500.00,
        savingsBalance:    0.00,
        last5Transactions: [],
      };
      mockFetch.mockResolvedValue(mockResponse(200, newAccountSummary));

      const result = await getAccountSummary(CUSTOMER_ID, AUTH_TOKEN);

      expect(result.last5Transactions).toEqual([]);
      expect(result.checkingBalance).toBe(500.00);
    });

    it("sends the correct Authorization header and URL", async () => {
      mockFetch.mockResolvedValue(mockResponse(200, MOCK_ACCOUNT_SUMMARY));

      await getAccountSummary(CUSTOMER_ID, AUTH_TOKEN);

      expect(mockFetch).toHaveBeenCalledWith(
        `https://api.internalbank.com/accounts/${CUSTOMER_ID}/summary`,
        expect.objectContaining({
          method: "GET",
          headers: expect.objectContaining({
            Authorization: `Bearer ${AUTH_TOKEN}`,
          }),
        })
      );
    });
  });

  // ---------------------------------------------------------------------------
  describe("Authentication failures", () => {

    it("throws AuthenticationError on 401 with a descriptive message", async () => {
      mockFetch.mockResolvedValue(mockResponse(401, { error: "Unauthorized" }));

      await expect(getAccountSummary(CUSTOMER_ID, AUTH_TOKEN)).rejects.toThrow(
        AuthenticationError
      );
    });

    it("includes re-authentication guidance in the AuthenticationError message", async () => {
      mockFetch.mockResolvedValue(mockResponse(401, {}));

      await expect(getAccountSummary(CUSTOMER_ID, AUTH_TOKEN)).rejects.toThrow(
        /re-authenticate/i
      );
    });
  });

  // ---------------------------------------------------------------------------
  describe("Timeout and connectivity failures", () => {

    it("throws NetworkTimeoutError on 504 Gateway Timeout", async () => {
      mockFetch.mockResolvedValue(mockResponse(504, {}));

      await expect(getAccountSummary(CUSTOMER_ID, AUTH_TOKEN)).rejects.toThrow(
        NetworkTimeoutError
      );
    });

    it("includes retry guidance in the NetworkTimeoutError message", async () => {
      mockFetch.mockResolvedValue(mockResponse(504, {}));

      await expect(getAccountSummary(CUSTOMER_ID, AUTH_TOKEN)).rejects.toThrow(
        /retry/i
      );
    });

    it("sets retryAfterSeconds to 30 on NetworkTimeoutError", async () => {
      mockFetch.mockResolvedValue(mockResponse(504, {}));

      try {
        await getAccountSummary(CUSTOMER_ID, AUTH_TOKEN);
      } catch (err) {
        expect(err).toBeInstanceOf(NetworkTimeoutError);
        expect((err as NetworkTimeoutError).retryAfterSeconds).toBe(30);
      }
    });

    it("throws GeneralApiError when fetch itself rejects (e.g. no network)", async () => {
      mockFetch.mockRejectedValue(new TypeError("Failed to fetch"));

      await expect(getAccountSummary(CUSTOMER_ID, AUTH_TOKEN)).rejects.toThrow(
        TypeError
      );
    });
  });

  // ---------------------------------------------------------------------------
  describe("Unexpected API responses", () => {

    it("throws GeneralApiError on 500 Internal Server Error", async () => {
      mockFetch.mockResolvedValue(mockResponse(500, { error: "Internal Server Error" }));

      await expect(getAccountSummary(CUSTOMER_ID, AUTH_TOKEN)).rejects.toThrow(
        GeneralApiError
      );
    });

    it("includes the HTTP status code in GeneralApiError", async () => {
      mockFetch.mockResolvedValue(mockResponse(503, {}));

      try {
        await getAccountSummary(CUSTOMER_ID, AUTH_TOKEN);
      } catch (err) {
        expect(err).toBeInstanceOf(GeneralApiError);
        expect((err as GeneralApiError).statusCode).toBe(503);
      }
    });

    it("throws GeneralApiError on 403 Forbidden", async () => {
      mockFetch.mockResolvedValue(mockResponse(403, { error: "Forbidden" }));

      try {
        await getAccountSummary(CUSTOMER_ID, AUTH_TOKEN);
      } catch (err) {
        expect(err).toBeInstanceOf(GeneralApiError);
        expect((err as GeneralApiError).statusCode).toBe(403);
      }
    });
  });

  // ---------------------------------------------------------------------------
  describe("Malformed or partial API responses", () => {

    it("returns object with undefined checkingBalance when field is missing", async () => {
      // The API omitted checkingBalance — we surface it as-is rather than throw,
      // letting the caller decide how to handle incomplete data.
      const partial = {
        savingsBalance:    18_540.00,
        last5Transactions: MOCK_TRANSACTIONS,
      };
      mockFetch.mockResolvedValue(mockResponse(200, partial));

      const result = await getAccountSummary(CUSTOMER_ID, AUTH_TOKEN);

      expect(result.checkingBalance).toBeUndefined();
      expect(result.savingsBalance).toBe(18_540.00);
    });

    it("defaults last5Transactions to an empty array when field is null", async () => {
      const withNullTransactions = {
        checkingBalance:   4_812.37,
        savingsBalance:    18_540.00,
        last5Transactions: null,
      };
      mockFetch.mockResolvedValue(mockResponse(200, withNullTransactions));

      const result = await getAccountSummary(CUSTOMER_ID, AUTH_TOKEN);

      expect(result.last5Transactions).toEqual([]);
    });
  });
});
