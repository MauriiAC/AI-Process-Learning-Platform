export type DemoRole = "admin" | "operator";

export interface User {
  id: string;
  name: string;
  email: string;
  location: string | null;
  demoRole: DemoRole;
}

export function getStoredUser(): User | null {
  const raw = localStorage.getItem("user");
  if (!raw) {
    return null;
  }

  const user = JSON.parse(raw) as Partial<User>;
  if (!user.id || !user.email || !user.name) {
    return null;
  }

  return {
    id: user.id,
    name: user.name,
    email: user.email,
    location: user.location ?? null,
    demoRole: user.demoRole ?? "operator",
  };
}

export function getDemoRole(): DemoRole | null {
  return getStoredUser()?.demoRole ?? null;
}

export function storeAuth(token: string, user: Omit<User, "demoRole">, demoRole: DemoRole) {
  localStorage.setItem("token", token);
  localStorage.setItem("user", JSON.stringify(user));
  const storedUser = getStoredUser();
  if (storedUser) {
    localStorage.setItem("user", JSON.stringify({ ...storedUser, demoRole }));
  }
}

export function clearAuth() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
}

export function isAuthenticated(): boolean {
  return !!localStorage.getItem("token") && !!getStoredUser();
}
