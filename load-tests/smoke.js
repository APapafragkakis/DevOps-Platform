import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  stages: [
    { duration: "1m", target: 3 },  // ramp up
    { duration: "1m",  target: 3 },  // hold
    { duration: "10s", target: 0  },  // ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95)<500"],  // 95% of requests under 500ms
    http_req_failed:   ["rate<0.05"],  // less than 1% errors
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export function setup() {
  const reg = http.post(`${BASE_URL}/auth/register`, JSON.stringify({
    username: "loadtest_user",
    password: "loadtest_pass",
  }), { headers: { "Content-Type": "application/json" } });

  const login = http.post(`${BASE_URL}/auth/token`,
    "username=loadtest_user&password=loadtest_pass",
    { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
  );

  return { token: JSON.parse(login.body).access_token };
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

  sleep(3);
}

