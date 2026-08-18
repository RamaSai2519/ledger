import {useAuthStore} from '@/state/authStore';

// `terraform output api_url` in infra/terraform — update if the stack is
// ever torn down and recreated (API Gateway assigns a new id).
const API_BASE_URL = 'https://w7ychchtd1.execute-api.ap-south-1.amazonaws.com';

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: {method?: string; body?: unknown; auth?: 'access' | 'refresh' | 'none'} = {},
): Promise<T> {
  const {method = 'GET', body, auth = 'access'} = options;
  const headers: Record<string, string> = {'Content-Type': 'application/json'};

  if (auth !== 'none') {
    const token =
      auth === 'refresh' ? useAuthStore.getState().refreshToken : useAuthStore.getState().accessToken;
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const json = await response.json();
  if (json.status !== 'SUCCESS') {
    throw new ApiError(json.error ?? 'unknown_error', response.status);
  }
  return json.data as T;
}

export type SignupInput = {mobile_number: string; password: string; name: string};
export type LoginInput = {mobile_number: string; password: string};
export type AuthTokens = {
  user_id: string;
  name: string;
  access_token: string;
  refresh_token: string;
  household_id?: string | null;
};

export const authApi = {
  signup: (input: SignupInput) => request<AuthTokens>('/auth/signup', {method: 'POST', body: input, auth: 'none'}),
  login: (input: LoginInput) => request<AuthTokens>('/auth/login', {method: 'POST', body: input, auth: 'none'}),
  logout: () => request<{logged_out: boolean}>('/auth/logout', {method: 'POST', auth: 'refresh'}),
};

export const householdApi = {
  create: (name: string) =>
    request<{household_id: string; name: string; invite_code: string}>('/auth/household/create', {
      method: 'POST',
      body: {name},
    }),
  join: (invite_code: string) =>
    request<{household_id: string; name: string; member_count: number}>('/auth/household/join', {
      method: 'POST',
      body: {invite_code},
    }),
  inviteCode: () =>
    request<{invite_code: string; household_id: string}>('/auth/household/invite-code'),
};

export {ApiError};
