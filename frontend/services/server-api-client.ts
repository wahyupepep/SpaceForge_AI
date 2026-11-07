import "server-only";

import { cookies } from "next/headers";

import { ApiClient, type RequestOptions } from "@/services/api-client";

export class ServerApiClient extends ApiClient {
  async request<ResponseBody>(path: string, options: RequestOptions = {}): Promise<ResponseBody> {
    const cookieStore = await cookies();
    const cookieHeader = cookieStore.toString();
    return super.request<ResponseBody>(path, {
      ...options,
      headers: {
        ...(cookieHeader ? { Cookie: cookieHeader } : {}),
        ...options.headers,
      },
    });
  }
}
