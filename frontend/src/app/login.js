import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Redirect, router } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';
import { colors } from '../theme/colors';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginScreen() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Redirect href={user.role === 'admin' ? '/admin' : '/therapist'} />;

  const onSubmit = async () => {
    if (submitting) return;
    setError('');
    setSubmitting(true);
    try {
      if (!EMAIL_RE.test(email.trim())) throw new Error('Please enter a valid email address.');
      if (!password) throw new Error('Please enter your password.');
      const u = await login(email, password);
      router.replace(u.role === 'admin' ? '/admin' : '/therapist');
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <View style={styles.brand}>
            <View style={styles.logo}>
              <MaterialCommunityIcons name="puzzle-heart" size={40} color={colors.primary} />
            </View>
            <Text style={styles.brandName}>Care Allocation Scheduler</Text>
            <Text style={styles.brandTag}>Therapy scheduling portal</Text>
          </View>

          <View style={styles.card}>
            <Text style={styles.title}>Welcome back</Text>
            <Text style={styles.subtitle}>Log in to view the session schedule.</Text>

            <Field
              label="Email"
              icon="email-outline"
              value={email}
              onChangeText={setEmail}
              placeholder="you@example.test"
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
            />
            <Field
              label="Password"
              icon="lock-outline"
              value={password}
              onChangeText={setPassword}
              placeholder="••••••••"
              secureTextEntry={!showPassword}
              trailing={
                <Pressable onPress={() => setShowPassword((s) => !s)} hitSlop={8}>
                  <MaterialCommunityIcons
                    name={showPassword ? 'eye-off-outline' : 'eye-outline'}
                    size={20}
                    color={colors.textMuted}
                  />
                </Pressable>
              }
              onSubmitEditing={onSubmit}
            />

            {!!error && (
              <View style={styles.error}>
                <MaterialCommunityIcons name="alert-circle-outline" size={18} color={colors.danger} />
                <Text style={styles.errorText}>{error}</Text>
              </View>
            )}

            <Pressable
              onPress={onSubmit}
              disabled={submitting}
              style={({ pressed }) => [styles.button, pressed && styles.buttonPressed, submitting && styles.buttonDisabled]}
              accessibilityRole="button"
            >
              <Text style={styles.buttonText}>{submitting ? 'Logging in…' : 'Log in'}</Text>
            </Pressable>

            <View style={styles.demo}>
              <Text style={styles.demoTitle}>Demo accounts</Text>
              <Text style={styles.demoText}>Admin: admin@example.test / demo123</Text>
              <Text style={styles.demoText}>Therapist: therapist01@example.test / demo123</Text>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Field({ label, icon, trailing, ...inputProps }) {
  const [focused, setFocused] = useState(false);
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <View style={[styles.inputWrap, focused && styles.inputWrapFocused]}>
        <MaterialCommunityIcons name={icon} size={20} color={focused ? colors.primary : colors.textMuted} />
        <TextInput
          style={styles.input}
          placeholderTextColor="#9AA8BD"
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          {...inputProps}
        />
        {trailing}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.primary },
  flex: { flex: 1 },
  scroll: { flexGrow: 1, justifyContent: 'center', padding: 20 },
  brand: { alignItems: 'center', marginBottom: 24 },
  logo: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colors.white,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  brandName: { color: colors.white, fontSize: 26, fontWeight: '700' },
  brandTag: { color: '#CFE0F7', fontSize: 14, marginTop: 4 },
  card: {
    backgroundColor: colors.white,
    borderRadius: 20,
    padding: 24,
    width: '100%',
    maxWidth: 460,
    alignSelf: 'center',
    boxShadow: '0 8px 20px rgba(11, 36, 71, 0.18)',
  },
  title: { fontSize: 22, fontWeight: '700', color: colors.text },
  subtitle: { fontSize: 14, color: colors.textMuted, marginTop: 4, marginBottom: 16 },
  label: { fontSize: 13, fontWeight: '600', color: colors.text, marginBottom: 6 },
  field: { marginBottom: 14 },
  inputWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: 12,
    paddingHorizontal: 12,
    backgroundColor: colors.white,
  },
  inputWrapFocused: { borderColor: colors.primary, backgroundColor: '#FBFDFF' },
  input: { flex: 1, paddingVertical: 12, fontSize: 15, color: colors.text, outlineStyle: 'none' },
  error: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: colors.dangerBg,
    padding: 10,
    borderRadius: 10,
    marginBottom: 12,
  },
  errorText: { color: colors.danger, flex: 1, fontSize: 13 },
  button: { backgroundColor: colors.primary, paddingVertical: 14, borderRadius: 12, alignItems: 'center', marginTop: 4 },
  buttonPressed: { backgroundColor: colors.primaryDark },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: colors.white, fontSize: 16, fontWeight: '700' },
  demo: { marginTop: 18, padding: 12, borderRadius: 10, backgroundColor: colors.sky },
  demoTitle: { fontWeight: '700', color: colors.primaryDark, marginBottom: 4, fontSize: 13 },
  demoText: { color: colors.textMuted, fontSize: 12 },
});
