import { createContext, useContext, useMemo, useState } from 'react';
import { fetchTherapistsByName } from '../data/api';

// Demo-only credentials. Authentication must be replaced before deployment.
const THERAPIST_NAMES = Array.from(
  { length: 29 },
  (_, index) => `Therapist ${String(index + 1).padStart(2, '0')}`,
);

const USERS = [
  { name: 'Demo Admin', email: 'admin@example.test', password: 'demo123', role: 'admin' },
  ...THERAPIST_NAMES.map((name, index) => {
    const loginName = `therapist${String(index + 1).padStart(2, '0')}`;
    return {
      name,
      email: `${loginName}@example.test`,
      password: 'demo123',
      role: 'therapist',
    };
  }),
];

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  const value = useMemo(
    () => ({
      user,
      async login(email, password) {
        const found = USERS.find(
          (u) => u.email.toLowerCase() === email.trim().toLowerCase() && u.password === password,
        );
        if (!found) throw new Error('Incorrect email or password.');
        let therapistId = null;
        let name = found.name;
        if (found.role === 'therapist') {
          const matches = await fetchTherapistsByName(found.name);
          if (matches.length !== 1) {
            throw new Error(`Expected one backend therapist named ${found.name}; found ${matches.length}.`);
          }
          therapistId = matches[0].id;
          name = matches[0].name;
        }
        const profile = { name, email: found.email, role: found.role, therapistId };
        setUser(profile);
        return profile;
      },
      logout() {
        setUser(null);
      },
    }),
    [user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
