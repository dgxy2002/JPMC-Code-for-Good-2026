import { Redirect, Stack } from 'expo-router';
import { useAuth } from '../../context/AuthContext';

export default function TherapistLayout() {
  const { user } = useAuth();
  if (!user) return <Redirect href="/login" />;
  if (user.role !== 'therapist') return <Redirect href="/admin" />;
  return <Stack screenOptions={{ headerShown: false }} />;
}
