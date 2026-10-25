import { StyleSheet, Text, View } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, levelColors } from '../theme/colors';

const LOCATION_STYLE = {
  Home: { fg: colors.home, bg: colors.homeBg, icon: 'home-outline' },
  School: { fg: colors.school, bg: colors.schoolBg, icon: 'school-outline' },
  Centre: { fg: colors.primary, bg: colors.sky, icon: 'office-building-outline' },
};

export default function SessionCard({ session, showTherapist, wide }) {
  const free = !session.student;
  const level = levelColors[session.level];
  const loc = LOCATION_STYLE[session.location];

  return (
    <View style={[styles.card, wide && styles.cardWide, free && styles.cardFree]}>
      <View style={[styles.accent, { backgroundColor: free ? colors.skyBorder : loc.fg }]} />
      <View style={styles.body}>
        <View style={styles.row}>
          <Text style={[styles.student, free && styles.freeText]} numberOfLines={1}>
            {free ? 'Available for replacement' : session.student}
          </Text>
          {!free && (
            <View style={[styles.badge, { backgroundColor: loc.bg }]}>
              <MaterialCommunityIcons name={loc.icon} size={12} color={loc.fg} />
              <Text style={[styles.badgeText, { color: loc.fg }]}>{session.location}</Text>
            </View>
          )}
        </View>

        {showTherapist && (
          <View style={styles.row}>
            <MaterialCommunityIcons name="account-tie" size={15} color={colors.textMuted} />
            <Text style={styles.therapist}>{session.therapist}</Text>
            <View style={[styles.level, { backgroundColor: level.bg }]}>
              <Text style={[styles.levelText, { color: level.fg }]}>{session.level}</Text>
            </View>
          </View>
        )}

        <View style={styles.row}>
          <MaterialCommunityIcons name="clock-outline" size={15} color={colors.textMuted} />
          <Text style={styles.time}>{session.time}</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    backgroundColor: colors.white,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: 'hidden',
  },
  cardWide: { width: '48.5%' },
  cardFree: { backgroundColor: '#FAFCFF', borderStyle: 'dashed', borderColor: colors.skyBorder },
  accent: { width: 5 },
  body: { flex: 1, padding: 12, gap: 6 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  student: { fontSize: 16, fontWeight: '700', color: colors.text, flex: 1 },
  freeText: { color: colors.textMuted, fontWeight: '600', fontSize: 14 },
  badge: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 999 },
  badgeText: { fontSize: 11, fontWeight: '700' },
  therapist: { color: colors.text, fontSize: 14 },
  level: { paddingHorizontal: 6, paddingVertical: 1, borderRadius: 6 },
  levelText: { fontSize: 10, fontWeight: '700' },
  time: { color: colors.textMuted, fontSize: 13 },
});
