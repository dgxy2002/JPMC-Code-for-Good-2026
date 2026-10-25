import { useEffect, useMemo, useRef, useState } from 'react';
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { router } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Calendar } from 'react-native-calendars';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';
import {
  fetchSessionsForMonth,
  fromDateString,
  getSessionsForDate,
  getSessionsForMonth,
  monthKey,
  toDateString,
} from '../data/schedule';
import { isReallocatableSession, planReallocation, submitReallocationPlan } from '../data/reschedule';
import { colors } from '../theme/colors';
import SessionCard from './SessionCard';

const RESCHEDULE_REASONS = [
  // 'Annual Leave',
  'Medical Leave',
  'Urgent Leave',
  'Others'
];

export default function ScheduleScreen({ mode }) {
  const isAdmin = mode === 'admin';
  const { user, logout } = useAuth();

  const today = toDateString(new Date());
  const [selected, setSelected] = useState(null);
  const [visibleMonth, setVisibleMonth] = useState(() => {
    const d = new Date();
    return { year: d.getFullYear(), month: d.getMonth() };
  });
  // Therapist reschedule picker: { start, end }. end stays null until a later
  // date is tapped, meaning "just this one day so far".
  const [range, setRange] = useState({ start: null, end: null });
  const [reasonModalOpen, setReasonModalOpen] = useState(false);
  const [reasonMenuOpen, setReasonMenuOpen] = useState(false);
  const [reason, setReason] = useState(null);
  const [confirmation, setConfirmation] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const submittingRef = useRef(false);
  const [sessionsByMonth, setSessionsByMonth] = useState({});
  const [monthStates, setMonthStates] = useState({});
  const [retryCount, setRetryCount] = useState(0);

  const mySessions = (dateString) =>
    getSessionsForDate(sessionsByMonth, dateString).filter(
      (s) => s.therapistId === user.therapistId && isReallocatableSession(s),
    );

  const addDays = (dateString, n) => {
    const d = fromDateString(dateString);
    d.setDate(d.getDate() + n);
    return toDateString(d);
  };

  const prettyDate = (dateString) =>
    fromDateString(dateString).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' });

  // All dates from range.start to (range.end ?? range.start), inclusive.
  const rangeDates = useMemo(() => {
    if (!range.start) return [];
    const end = range.end || range.start;
    const dates = [];
    let d = range.start;
    while (true) {
      dates.push(d);
      if (d === end) break;
      d = addDays(d, 1);
    }
    return dates;
  }, [range]);

  const rangeReady = rangeDates.every((date) => !!sessionsByMonth[date.slice(0, 7)]);
  const reallocationPlan = useMemo(
    () => planReallocation(rangeDates, sessionsByMonth, user.therapistId),
    [rangeDates, sessionsByMonth, user.therapistId],
  );

  const visibleMonthKey = monthKey(visibleMonth.year, visibleMonth.month);
  const visibleSessions = useMemo(
    () => getSessionsForMonth(sessionsByMonth, visibleMonth.year, visibleMonth.month).filter(
      (session) => session.status !== 'CANCELLED' && (isAdmin || session.therapistId === user.therapistId),
    ),
    [sessionsByMonth, visibleMonth, isAdmin, user.therapistId],
  );
  const listSessions = isAdmin && selected
    ? visibleSessions.filter((session) => session.date === selected)
    : visibleSessions;
  const neededMonthKeys = [...new Set([visibleMonthKey, ...rangeDates.map((date) => date.slice(0, 7))])].join(',');

  useEffect(() => {
    const controller = new AbortController();
    for (const key of neededMonthKeys.split(',')) {
      const [year, month] = key.split('-').map(Number);
      setMonthStates((prev) => ({ ...prev, [key]: { loading: true, error: null } }));
      fetchSessionsForMonth(year, month - 1, controller.signal)
        .then((sessions) => {
          if (controller.signal.aborted) return;
          setSessionsByMonth((prev) => ({ ...prev, [key]: sessions }));
          setMonthStates((prev) => ({ ...prev, [key]: { loading: false, error: null } }));
        })
        .catch((error) => {
          if (controller.signal.aborted) return;
          setMonthStates((prev) => ({ ...prev, [key]: { loading: false, error: error.message } }));
        });
    }
    return () => controller.abort();
  }, [neededMonthKeys, retryCount]);

  const markedDates = useMemo(() => {
    const marks = {};
    const seenByDate = {};
    for (const session of visibleSessions) {
      const date = session.date;
      const key = `${session.student_id}-${session.slot}`;
      if (!marks[date]) {
        marks[date] = { items: [] };
        seenByDate[date] = new Set();
      }
      if (seenByDate[date].has(key)) continue;
      seenByDate[date].add(key);
      marks[date].items.push({ student: session.student, slot: session.slot });
    }
    if (isAdmin && selected) {
      marks[selected] = { ...marks[selected], selected: true };
    } else {
      for (const d of rangeDates) {
        marks[d] = { ...marks[d], rescheduleSelected: true };
      }
    }
    return marks;
  }, [visibleSessions, selected, rangeDates, isAdmin]);

  // Tap 1 sets the start. Tap 2 after it: on/after start extends the range
  // through that day; before start, it's ambiguous (single day vs. new
  // start) so we just move the start there and wait for the next tap.
  const onDayPress = (day) => {
    const d = day.dateString;
    if (d < today) return;
    if (isAdmin) {
      setSelected(d);
      return;
    }
    setReason(null);
    setRange((prev) => {
      if (!prev.start || prev.end) return { start: d, end: null };
      if (d < prev.start) return { start: d, end: null };
      return { start: prev.start, end: d };
    });
  };

  const onLogout = () => {
    logout();
    router.replace('/login');
  };

  const onAddStudent = () => {
    router.navigate('/admin/add-student');
  };

  const onRequestReschedule = () => {
    if (!rangeReady || !reallocationPlan.targets.length) return;
    setReasonMenuOpen(false);
    setReasonModalOpen(true);
  };

  const refreshAffectedMonths = async (dates) => {
    const failedMonths = [];
    for (const key of new Set(dates.map((date) => date.slice(0, 7)))) {
      const [year, month] = key.split('-').map(Number);
      try {
        const sessions = await fetchSessionsForMonth(year, month - 1);
        setSessionsByMonth((prev) => ({ ...prev, [key]: sessions }));
        setMonthStates((prev) => ({ ...prev, [key]: { loading: false, error: null } }));
      } catch (error) {
        setSessionsByMonth((prev) => {
          const next = { ...prev };
          delete next[key];
          return next;
        });
        setMonthStates((prev) => ({ ...prev, [key]: { loading: false, error: error.message } }));
        failedMonths.push(key);
      }
    }
    return failedMonths;
  };

  const onConfirmReason = async () => {
    if (submittingRef.current || !reason || !rangeReady || !reallocationPlan.targets.length) return;
    submittingRef.current = true;
    setSubmitting(true);
    try {
      const outcome = await submitReallocationPlan(reallocationPlan.targets, user.therapistId, reason);
      const failedMonths = await refreshAffectedMonths(reallocationPlan.targets.map(({ date }) => date));
      setConfirmation({ ...outcome, skippedDates: reallocationPlan.skippedDates, failedMonths, reason });
      setReasonModalOpen(false);
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  };

  const onCloseConfirmation = () => {
    const hasFailures = confirmation?.failedDates.length > 0;
    setConfirmation(null);
    if (!hasFailures) {
      setReason(null);
      setRange({ start: null, end: null });
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <MaterialCommunityIcons name="puzzle-heart" size={28} color={colors.white} />
          <View>
            <Text style={styles.headerTitle}>{isAdmin ? 'Centre Schedule' : 'My Schedule'}</Text>
            <Text style={styles.headerSub}>
              {user.name} · {isAdmin ? 'Admin' : 'Therapist'}
            </Text>
          </View>
        </View>
        <View style={styles.headerActions}>
          {isAdmin && (
            <Pressable
              onPress={onAddStudent}
              style={styles.addStudent}
              accessibilityRole="button"
              accessibilityLabel="Add student"
            >
              <MaterialCommunityIcons name="account-plus-outline" size={18} color={colors.white} />
              <Text style={styles.addStudentText}>Add Student</Text>
            </Pressable>
          )}
          <Pressable onPress={onLogout} style={styles.logout} accessibilityLabel="Log out">
            <MaterialCommunityIcons name="logout" size={18} color={colors.primary} />
            <Text style={styles.logoutText}>Log out</Text>
          </Pressable>
        </View>
      </View>

      <ScrollView style={styles.body} contentContainerStyle={styles.content}>
        <View style={styles.panel}>
          <Calendar
            initialDate={today}
            onDayPress={onDayPress}
            onMonthChange={(m) => { setVisibleMonth({ year: m.year, month: m.month - 1 }); setSelected(null); }}
            markedDates={markedDates}
            minDate={today}
            disableAllTouchEventsForDisabledDays
            firstDay={1}
            enableSwipeMonths
            theme={calendarTheme}
            dayComponent={DayCell}
          />
          <View style={styles.legend}>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: colors.home }]} />
              <Text style={styles.legendText}>Morning</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: colors.school }]} />
              <Text style={styles.legendText}>Afternoon</Text>
            </View>
            <Pressable onPress={() => setSelected(today)} style={styles.todayBtn}>
              <Text style={styles.todayText}>Today</Text>
            </Pressable>
          </View>
          {monthStates[visibleMonthKey]?.error ? (
            <View style={styles.loadBox}>
              <Text style={styles.loadError}>{monthStates[visibleMonthKey].error}</Text>
              <Pressable onPress={() => setRetryCount((count) => count + 1)}>
                <Text style={styles.retryText}>Retry</Text>
              </Pressable>
            </View>
          ) : !sessionsByMonth[visibleMonthKey] ? (
            <Text style={styles.loadMessage}>Loading sessions…</Text>
          ) : visibleSessions.length === 0 ? (
            <Text style={styles.loadMessage}>
              {!isAdmin && sessionsByMonth[visibleMonthKey].length > 0
                ? `No sessions are currently assigned to ${user.name} this month.`
                : 'No sessions on this schedule this month.'}
            </Text>
          ) : null}
        </View>

        <View style={styles.sessionsPanel}>
          <View style={styles.sessionsHeader}>
            <View>
              <Text style={styles.sessionsTitle}>Sessions ({listSessions.length})</Text>
              <Text style={styles.sessionsSubtitle}>
                {selected && isAdmin ? prettyDate(selected) : new Date(visibleMonth.year, visibleMonth.month).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}
              </Text>
            </View>
            {selected && isAdmin && (
              <Pressable onPress={() => setSelected(null)} accessibilityRole="button" accessibilityLabel="Show all sessions this month">
                <Text style={styles.showAllText}>Show all month</Text>
              </Pressable>
            )}
          </View>
          {sessionsByMonth[visibleMonthKey] && (
            listSessions.length ? listSessions.map((session) => (
              <View key={session.id} style={styles.sessionListItem}>
                <View style={styles.sessionListMeta}>
                  <Text style={styles.sessionDate}>{prettyDate(session.date)}</Text>
                  <Text style={styles.sessionStatus}>{session.status.replaceAll('_', ' ')}</Text>
                </View>
                <SessionCard session={session} showTherapist={isAdmin} />
              </View>
            )) : (
              <Text style={styles.rescheduleEmpty}>
                No sessions {selected && isAdmin ? 'on this day' : 'this month'}.
              </Text>
            )
          )}
        </View>

        {!isAdmin && (
          <View style={styles.reschedulePanel}>
            <View style={styles.rescheduleHeader}>
              <Text style={styles.rescheduleTitle}>
                Tap a day to reallocate its sessions. Tap a later day to include every day in between.
              </Text>
              {range.start && (
                <Pressable onPress={() => { setRange({ start: null, end: null }); setReason(null); }}>
                  <Text style={styles.clearText}>Clear</Text>
                </Pressable>
              )}
            </View>

            {!range.start ? (
              <Text style={styles.rescheduleEmpty}>No dates selected yet.</Text>
            ) : (
              <>
                {!range.end && (
                  <Text style={styles.rescheduleHint}>
                    Tap an earlier day to move the start, or a later day to extend the range.
                  </Text>
                )}

                {rangeDates.map((date) => (
                  <View key={date} style={styles.rescheduleBlock}>
                    <Text style={styles.rescheduleBlockDate}>{prettyDate(date)}</Text>
                    {!sessionsByMonth[date.slice(0, 7)] && (
                      <View>
                        <Text style={monthStates[date.slice(0, 7)]?.error ? styles.loadError : styles.rescheduleEmpty}>
                          {monthStates[date.slice(0, 7)]?.error || 'Loading sessions…'}
                        </Text>
                        {monthStates[date.slice(0, 7)]?.error && (
                          <Pressable onPress={() => setRetryCount((count) => count + 1)}>
                            <Text style={styles.retryText}>Retry loading</Text>
                          </Pressable>
                        )}
                      </View>
                    )}
                    {mySessions(date).map((s) => (
                      <SessionCard key={s.id} session={s} />
                    ))}
                    {sessionsByMonth[date.slice(0, 7)] && mySessions(date).length === 0 && (
                      <Text style={styles.rescheduleEmpty}>No sessions for this date.</Text>
                    )}
                  </View>
                ))}

                {rangeReady && reallocationPlan.skippedDates.length > 0 && (
                  <Text style={styles.rescheduleHint}>
                    {reallocationPlan.skippedDates.length} selected {reallocationPlan.skippedDates.length === 1 ? 'day has' : 'days have'} no sessions to reallocate and will be skipped.
                  </Text>
                )}

                <Pressable
                  style={[styles.submitBtn, (!rangeReady || !reallocationPlan.targets.length) && styles.submitBtnDisabled]}
                  disabled={!rangeReady || !reallocationPlan.targets.length}
                  onPress={onRequestReschedule}
                >
                  <Text style={styles.submitText}>
                    {!rangeReady
                      ? 'Loading selected dates…'
                      : reallocationPlan.targets.length
                        ? `Reallocate sessions on ${reallocationPlan.targets.length} ${reallocationPlan.targets.length === 1 ? 'day' : 'days'}`
                        : 'No sessions to reallocate'}
                  </Text>
                </Pressable>
              </>
            )}
          </View>
        )}
      </ScrollView>

      <Modal visible={reasonModalOpen} transparent animationType="fade" onRequestClose={() => !submitting && setReasonModalOpen(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Reason for reschedule</Text>
            <Text style={styles.modalSubtitle}>
              {rangeDates.length > 1
                ? `${prettyDate(range.start)} – ${prettyDate(range.end)}`
                : range.start && prettyDate(range.start)}
            </Text>
            <Text style={styles.confirmNote}>This records your reason and updates your AM and PM sessions on each selected day. Sessions without a replacement will be cancelled.</Text>

            <Pressable style={styles.selectRow} disabled={submitting} onPress={() => setReasonMenuOpen((v) => !v)}>
              <Text style={[styles.selectText, !reason && styles.selectPlaceholder]}>
                {reason || 'Select a reason'}
              </Text>
              <MaterialCommunityIcons name={reasonMenuOpen ? 'chevron-up' : 'chevron-down'} size={20} color={colors.textMuted} />
            </Pressable>

            {reasonMenuOpen && (
              <View style={styles.optionsList}>
                {RESCHEDULE_REASONS.map((opt) => (
                  <Pressable
                    key={opt}
                    style={styles.optionItem}
                    onPress={() => {
                      setReason(opt);
                      setReasonMenuOpen(false);
                    }}
                  >
                    <Text style={styles.optionText}>{opt}</Text>
                    {reason === opt && <MaterialCommunityIcons name="check" size={16} color={colors.primary} />}
                  </Pressable>
                ))}
              </View>
            )}

            <View style={styles.modalActions}>
              <Pressable style={styles.cancelBtn} disabled={submitting} onPress={() => setReasonModalOpen(false)}>
                <Text style={styles.cancelText}>Cancel</Text>
              </Pressable>
              <Pressable
                style={[styles.okBtn, (!reason || submitting) && styles.okBtnDisabled]}
                disabled={!reason || submitting}
                onPress={onConfirmReason}
              >
                <Text style={styles.okText}>{submitting ? 'Updating…' : 'Confirm'}</Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>

      <Modal visible={!!confirmation} transparent animationType="fade" onRequestClose={onCloseConfirmation}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <MaterialCommunityIcons
              name={confirmation?.failedDates.length ? 'alert-circle' : 'check-circle'}
              size={40}
              color={confirmation?.failedDates.length ? colors.reschedule : colors.home}
              style={styles.confirmIcon}
            />
            <Text style={styles.confirmTitle}>
              {confirmation?.failedDates.length ? 'Some dates need attention' : 'Schedule updated'}
            </Text>
            {confirmation && (
              <>
                <View style={styles.confirmRow}>
                  <Text style={styles.confirmLabel}>Updated days</Text>
                  <Text style={styles.confirmValue}>{confirmation.successfulDates.length}</Text>
                </View>
                {confirmation.successfulDates.length > 0 && (
                  <View style={styles.confirmRow}>
                    <Text style={styles.confirmLabel}>Recorded reason</Text>
                    <Text style={styles.confirmValue}>{confirmation.reason}</Text>
                  </View>
                )}
                {confirmation.skippedDates.length > 0 && (
                  <Text style={styles.confirmNote}>{confirmation.skippedDates.length} day(s) had no sessions to reallocate and were skipped.</Text>
                )}
                {confirmation.failedDates.length > 0 && (
                  <ScrollView style={styles.failureList}>
                    {confirmation.failedDates.map(({ date, message }) => (
                      <Text key={date} style={styles.loadError}>{prettyDate(date)}: {message}</Text>
                    ))}
                  </ScrollView>
                )}
                {confirmation.failedMonths.length > 0 && (
                  <Text style={styles.loadError}>Could not refresh the schedule. Use Retry on the calendar.</Text>
                )}
              </>
            )}
            {confirmation?.failedDates.length > 0 && (
              <Text style={styles.confirmNote}>Your selected dates remain available for retry.</Text>
            )}
            <Pressable style={styles.doneBtn} onPress={onCloseConfirmation}>
              <Text style={styles.submitText}>Done</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

// Custom cell: lists each day's students (color-coded AM/PM) and highlights
// the therapist's selected reschedule day.
function DayCell({ date, state, marking, onPress }) {
  const m = marking || {};
  const disabled = state === 'disabled';
  const items = m.items || [];
  const shown = items.slice(0, 3);
  const extra = items.length - shown.length;
  const highlighted = m.selected || m.rescheduleSelected;

  return (
    <Pressable onPress={() => onPress(date)} disabled={disabled} style={styles.dayCell}>
      <View
        style={[
          styles.dayNumWrap,
          state === 'today' && !highlighted && styles.dayNumToday,
          m.selected && { backgroundColor: colors.primary },
          m.rescheduleSelected && { backgroundColor: colors.reschedule },
        ]}
      >
        <Text style={[styles.dayNum, disabled && styles.dayNumDisabled, highlighted && styles.dayNumTextLight]}>
          {date.day}
        </Text>
      </View>
      {shown.map((it) => (
        <Text
          key={`${it.student}-${it.slot}`}
          style={[styles.dayStudent, { color: it.slot === 'AM' ? colors.home : colors.school }]}
          numberOfLines={1}
        >
          {it.student}
        </Text>
      ))}
      {extra > 0 && <Text style={styles.dayStudentMore}>+{extra} more</Text>}
    </Pressable>
  );
}

const calendarTheme = {
  calendarBackground: colors.white,
  textSectionTitleColor: colors.textMuted,
  arrowColor: colors.primary,
  monthTextColor: colors.primaryDark,
  textMonthFontWeight: '700',
  textMonthFontSize: 18,
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.primary },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 14,
    backgroundColor: colors.primary,
  },
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 12, flexShrink: 1 },
  headerTitle: { color: colors.white, fontSize: 20, fontWeight: '700' },
  headerSub: { color: '#CFE0F7', fontSize: 13, marginTop: 2 },
  headerActions: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  addStudent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: colors.primaryDark,
    paddingHorizontal: 11,
    paddingVertical: 8,
    borderRadius: 999,
  },
  addStudentText: { color: colors.white, fontWeight: '700', fontSize: 13 },
  logout: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: colors.white,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 999,
  },
  logoutText: { color: colors.primary, fontWeight: '600', fontSize: 13 },
  body: { flex: 1, backgroundColor: colors.background },
  content: { padding: 16, gap: 16, maxWidth: 640, width: '100%', alignSelf: 'center' },
  panel: {
    backgroundColor: colors.white,
    borderRadius: 16,
    padding: 8,
    borderWidth: 1,
    borderColor: colors.border,
  },
  legend: { flexDirection: 'row', alignItems: 'center', gap: 14, paddingHorizontal: 12, paddingVertical: 10 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendDot: { width: 8, height: 8, borderRadius: 4 },
  legendText: { color: colors.textMuted, fontSize: 12 },
  loadBox: { paddingHorizontal: 12, paddingBottom: 12 },
  loadMessage: { paddingHorizontal: 12, paddingBottom: 12, color: colors.textMuted, fontSize: 13 },
  loadError: { color: colors.danger, fontSize: 13 },
  sessionsPanel: { gap: 12 },
  sessionsHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  sessionsTitle: { color: colors.text, fontSize: 18, fontWeight: '700' },
  sessionsSubtitle: { color: colors.textMuted, fontSize: 13, marginTop: 2 },
  showAllText: { color: colors.primary, fontSize: 13, fontWeight: '700' },
  sessionListItem: { gap: 6 },
  sessionListMeta: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  sessionDate: { color: colors.text, fontSize: 14, fontWeight: '700' },
  sessionStatus: { color: colors.home, fontSize: 12, fontWeight: '700' },
  retryText: { color: colors.primary, fontWeight: '700', marginTop: 6 },
  todayBtn: { marginLeft: 'auto', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 999, backgroundColor: colors.sky },
  todayText: { color: colors.primary, fontWeight: '600', fontSize: 12 },
  dayCell: { width: '100%', alignItems: 'center', paddingVertical: 4, gap: 1, minHeight: 66 },
  dayNumWrap: { width: 24, height: 24, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  dayNumToday: { backgroundColor: colors.sky },
  dayNum: { fontSize: 13, fontWeight: '600', color: colors.text },
  dayNumDisabled: { color: '#C3CCDA' },
  dayNumTextLight: { color: colors.white },
  dayStudent: { fontSize: 12, fontWeight: '600', lineHeight: 14, maxWidth: 58 },
  dayStudentMore: { fontSize: 10, color: colors.textMuted },
  reschedulePanel: { gap: 12 },
  rescheduleHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
  rescheduleTitle: { fontSize: 14, fontWeight: '600', color: colors.text, flex: 1 },
  clearText: { color: colors.reschedule, fontWeight: '700', fontSize: 13 },
  rescheduleEmpty: { color: colors.textMuted, fontSize: 13 },
  rescheduleHint: { color: colors.textMuted, fontSize: 12, fontStyle: 'italic' },
  rescheduleBlock: { gap: 8 },
  rescheduleBlockDate: { fontSize: 15, fontWeight: '700', color: colors.reschedule },
  submitBtn: {
    backgroundColor: colors.reschedule,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
  },
  submitBtnDisabled: { opacity: 0.5 },
  submitText: { color: colors.white, fontWeight: '700', fontSize: 14 },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(19,41,75,0.45)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  modalCard: {
    width: '100%',
    maxWidth: 360,
    backgroundColor: colors.white,
    borderRadius: 16,
    padding: 20,
    gap: 12,
  },
  modalTitle: { fontSize: 17, fontWeight: '700', color: colors.text },
  modalSubtitle: { fontSize: 13, color: colors.textMuted, marginTop: -8 },
  selectRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
  selectText: { fontSize: 14, color: colors.text, fontWeight: '600' },
  selectPlaceholder: { color: colors.textMuted, fontWeight: '400' },
  optionsList: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    overflow: 'hidden',
  },
  optionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    paddingVertical: 11,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  optionText: { fontSize: 14, color: colors.text },
  modalActions: { flexDirection: 'row', gap: 10, marginTop: 4 },
  cancelBtn: {
    flex: 1,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  cancelText: { color: colors.textMuted, fontWeight: '600', fontSize: 14 },
  okBtn: {
    flex: 1,
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
  },
  okBtnDisabled: { opacity: 0.4 },
  okText: { color: colors.white, fontWeight: '700', fontSize: 14 },
  confirmIcon: { alignSelf: 'center' },
  confirmTitle: { fontSize: 17, fontWeight: '700', color: colors.text, textAlign: 'center' },
  confirmRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  confirmLabel: { fontSize: 13, color: colors.textMuted },
  confirmValue: { fontSize: 13, fontWeight: '700', color: colors.text },
  confirmNote: { fontSize: 12, color: colors.textMuted, textAlign: 'center' },
  failureList: { maxHeight: 130 },
  doneBtn: {
    backgroundColor: colors.home,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
    marginTop: 4,
  },
});
