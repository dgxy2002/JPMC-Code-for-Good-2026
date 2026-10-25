import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { router } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { createStudent } from '../../data/api';
import { colors } from '../../theme/colors';


const SENIORITY_OPTIONS = [
  {
    value: 'ANY',
    label: 'Any level',
    description: 'Either junior or senior therapists can be considered.',
  },
  {
    value: 'JUNIOR',
    label: 'Junior',
    description: 'Prefer a junior therapist, with senior fallback.',
  },
  {
    value: 'SENIOR',
    label: 'Senior',
    description: 'Prefer a senior therapist, with junior fallback.',
  },
];


export default function AddStudentScreen() {
  const [name, setName] = useState('');
  const [requiredSeniority, setRequiredSeniority] = useState('ANY');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [createdStudent, setCreatedStudent] = useState(null);

  const normalizedName = name.trim();
  const canSubmit = normalizedName.length > 0 && !submitting;

  const clearFeedback = () => {
    setError(null);
    setCreatedStudent(null);
  };

  const onSubmit = async () => {
    if (!canSubmit) {
      if (!normalizedName) setError('Enter the student\'s name.');
      return;
    }

    setSubmitting(true);
    setError(null);
    setCreatedStudent(null);
    try {
      const student = await createStudent({
        name: normalizedName,
        required_seniority: requiredSeniority,
      });
      setCreatedStudent(student);
      setName('');
      setRequiredSeniority('ANY');
    } catch (requestError) {
      setError(requestError.message || 'Could not add the student. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <Pressable
          onPress={() => router.back()}
          style={styles.backButton}
          accessibilityRole="button"
          accessibilityLabel="Back to centre schedule"
        >
          <MaterialCommunityIcons name="arrow-left" size={22} color={colors.white} />
        </Pressable>
        <View style={styles.headerCopy}>
          <Text style={styles.headerTitle}>Add Student</Text>
          <Text style={styles.headerSubtitle}>Create a student profile</Text>
        </View>
      </View>

      <ScrollView
        style={styles.body}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.intro}>
          <MaterialCommunityIcons name="account-plus-outline" size={28} color={colors.primary} />
          <View style={styles.introCopy}>
            <Text style={styles.introTitle}>Student details</Text>
            <Text style={styles.introText}>
              Add the student's name and the therapist seniority they require.
            </Text>
          </View>
        </View>

        <View style={styles.formCard}>
          <View style={styles.field}>
            <Text style={styles.label}>Student name</Text>
            <Text style={styles.required}>Required</Text>
            <TextInput
              value={name}
              onChangeText={(value) => {
                setName(value);
                clearFeedback();
              }}
              editable={!submitting}
              maxLength={100}
              autoCapitalize="words"
              autoCorrect={false}
              returnKeyType="done"
              onSubmitEditing={onSubmit}
              placeholder="Enter the student's full name"
              placeholderTextColor="#8A98AD"
              style={styles.input}
              accessibilityLabel="Student name"
            />
            <Text style={styles.counter}>{name.length}/100</Text>
          </View>

          <View style={styles.field}>
            <Text style={styles.label}>Required therapist seniority</Text>
            <Text style={styles.required}>Required</Text>
            <View style={styles.options}>
              {SENIORITY_OPTIONS.map((option) => {
                const selected = requiredSeniority === option.value;
                return (
                  <Pressable
                    key={option.value}
                    onPress={() => {
                      setRequiredSeniority(option.value);
                      clearFeedback();
                    }}
                    disabled={submitting}
                    style={[styles.option, selected && styles.optionSelected]}
                    accessibilityRole="radio"
                    accessibilityState={{ checked: selected, disabled: submitting }}
                  >
                    <View style={[styles.radio, selected && styles.radioSelected]}>
                      {selected && <View style={styles.radioDot} />}
                    </View>
                    <View style={styles.optionCopy}>
                      <Text style={[styles.optionLabel, selected && styles.optionLabelSelected]}>
                        {option.label}
                      </Text>
                      <Text style={styles.optionDescription}>{option.description}</Text>
                    </View>
                  </Pressable>
                );
              })}
            </View>
          </View>

          {error && (
            <View style={styles.errorBox} accessibilityRole="alert">
              <MaterialCommunityIcons name="alert-circle-outline" size={20} color={colors.danger} />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          {createdStudent && (
            <View style={styles.successBox} accessibilityRole="alert">
              <MaterialCommunityIcons name="check-circle-outline" size={22} color={colors.home} />
              <View style={styles.feedbackCopy}>
                <Text style={styles.successTitle}>Student added</Text>
                <Text style={styles.successText}>
                  {createdStudent.name} was added successfully.
                </Text>
              </View>
            </View>
          )}

          <Pressable
            onPress={onSubmit}
            disabled={!canSubmit}
            style={[styles.submitButton, !canSubmit && styles.submitButtonDisabled]}
            accessibilityRole="button"
            accessibilityState={{ disabled: !canSubmit, busy: submitting }}
          >
            <MaterialCommunityIcons
              name={submitting ? 'progress-clock' : 'account-plus'}
              size={20}
              color={colors.white}
            />
            <Text style={styles.submitText}>{submitting ? 'Adding student…' : 'Add Student'}</Text>
          </Pressable>

          <Pressable
            onPress={() => router.back()}
            disabled={submitting}
            style={styles.cancelButton}
            accessibilityRole="button"
          >
            <Text style={styles.cancelText}>Back to schedule</Text>
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}


const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.primary },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    backgroundColor: colors.primary,
  },
  backButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.primaryDark,
  },
  headerCopy: { flex: 1 },
  headerTitle: { color: colors.white, fontSize: 20, fontWeight: '700' },
  headerSubtitle: { color: '#CFE0F7', fontSize: 13, marginTop: 2 },
  body: { flex: 1, backgroundColor: colors.background },
  content: {
    width: '100%',
    maxWidth: 640,
    alignSelf: 'center',
    padding: 16,
    gap: 16,
  },
  intro: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 16,
    borderRadius: 16,
    backgroundColor: colors.sky,
    borderWidth: 1,
    borderColor: colors.skyBorder,
  },
  introCopy: { flex: 1 },
  introTitle: { color: colors.primaryDark, fontSize: 17, fontWeight: '700' },
  introText: { color: colors.textMuted, fontSize: 13, lineHeight: 19, marginTop: 3 },
  formCard: {
    gap: 20,
    padding: 18,
    borderRadius: 16,
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.border,
  },
  field: { gap: 8 },
  label: { color: colors.text, fontSize: 15, fontWeight: '700' },
  required: { color: colors.textMuted, fontSize: 12, marginTop: -5 },
  input: {
    minHeight: 48,
    paddingHorizontal: 13,
    paddingVertical: 11,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.skyBorder,
    backgroundColor: colors.white,
    color: colors.text,
    fontSize: 15,
  },
  counter: { alignSelf: 'flex-end', color: colors.textMuted, fontSize: 11 },
  options: { gap: 9 },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 11,
    padding: 13,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.white,
  },
  optionSelected: { borderColor: colors.primary, backgroundColor: colors.sky },
  radio: {
    width: 20,
    height: 20,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: colors.skyBorder,
  },
  radioSelected: { borderColor: colors.primary },
  radioDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: colors.primary },
  optionCopy: { flex: 1 },
  optionLabel: { color: colors.text, fontSize: 14, fontWeight: '700' },
  optionLabelSelected: { color: colors.primaryDark },
  optionDescription: { color: colors.textMuted, fontSize: 12, lineHeight: 17, marginTop: 2 },
  errorBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 9,
    padding: 12,
    borderRadius: 10,
    backgroundColor: colors.dangerBg,
  },
  errorText: { flex: 1, color: colors.danger, fontSize: 13, fontWeight: '600' },
  successBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 9,
    padding: 12,
    borderRadius: 10,
    backgroundColor: colors.homeBg,
  },
  feedbackCopy: { flex: 1 },
  successTitle: { color: colors.home, fontSize: 14, fontWeight: '700' },
  successText: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
  submitButton: {
    minHeight: 48,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderRadius: 12,
    backgroundColor: colors.primary,
  },
  submitButtonDisabled: { opacity: 0.45 },
  submitText: { color: colors.white, fontSize: 15, fontWeight: '700' },
  cancelButton: { alignItems: 'center', paddingVertical: 8 },
  cancelText: { color: colors.primary, fontSize: 14, fontWeight: '700' },
});
