import { env } from "@/lib/env";

import type { ApiErrorResponse } from "@/types/api";

export class ApiClientError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details: Array<Record<string, unknown>> = [],
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
};

export class ApiClient {
  constructor(private readonly baseUrl: string = env.apiBaseUrl) {}

  async request<ResponseBody>(path: string, options: RequestOptions = {}): Promise<ResponseBody> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      headers: {
        Accept: "application/json",
        ...(options.body === undefined ? {} : { "Content-Type": "application/json" }),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const payload = (await response.json()) as ApiErrorResponse;
      throw new ApiClientError(
        response.status,
        payload.error.code,
        payload.error.message,
        payload.error.details,
      );
    }

    if (response.status === 204) {
      return undefined as ResponseBody;
    }

    return (await response.json()) as ResponseBody;
  }
}

export const apiClient = new ApiClient();
