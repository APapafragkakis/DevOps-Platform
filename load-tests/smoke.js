import http from "k6/http";
import { check, sleep } from "k6";

// Kept under the API rate limits (30 writes/min, 60 reads/min per IP),
// otherwise 429s show up as failed requests.
export const options = {
  stages: [
    { duration: "20s", target: 2 },
    { duration: "40s", target: 2 },
    { duration: "10s", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<500"],
    http_req_failed: ["rate<0.01"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export function setup() {
  http.post(`${BASE_URL}/auth/register`, JSON.stringify({
    username: "loadtest_user",
    password: "loadtest_pass",
  }), { headers: { "Content-Type": "application/json" } });

  const login = http.post(`${BASE_URL}/auth/token`,
    "username=loadtest_user&password=loadtest_pass",
    { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
  );
  check(login, { "login 200": (r) => r.status === 200 });

  return { token: login.json("access_token") };
}

export default function (data) {
  const headers = {
    Authorization: `Bearer ${data.token}`,
    "Content-Type": "application/json",
  };

  const health = http.get(`${BASE_URL}/health`);
  check(health, { "health 200": (r) => r.status === 200 });

  const list = http.get(`${BASE_URL}/items`, { headers });
  check(list, { "items 200": (r) => r.status === 200 });

  const create = http.post(`${BASE_URL}/items`,
    JSON.stringify({ name: `item-${Date.now()}`, description: "load test" }),
    { headers }
  );
  check(create, { "create 201": (r) => r.status === 201 });

  sleep(5);
}
