import os, sqlite3, tempfile, unittest
from unittest import mock
from core import ambience, sound_ai, sound_lib, sfx_plan
from core.db import connect

class ClassificationTests(unittest.TestCase):
    def test_summary_separates_human_and_accent(self):
        for label, voice, accent in [('Cricket',False,False),('Wind',False,False),('Speech',True,False),('Explosion',False,True),('Toilet flush',False,False)]:
            info = sound_ai.summary([(label, .9)])
            self.assertEqual(info['voice'], voice, label)
            self.assertEqual(info['accent'], accent, label)

    def test_summary_normalizes_classification_but_preserves_label(self):
        for label, voice, accent in [(' Speech ', True, False), (' Explosion ', False, True),
                                     (' Unknown class ', False, False), ('   ', False, False)]:
            info = sound_ai.summary([(label, .9)])
            self.assertEqual(info['voice'], voice, label)
            self.assertEqual(info['accent'], accent, label)
            self.assertEqual(info['label'], label)
        self.assertEqual(sound_ai.summary([])['accent'], False)
        with mock.patch.object(sound_ai, 'ACCENT', sound_ai.ACCENT | {'speech'}):
            info = sound_ai.summary([(' Speech ', .9)])
            self.assertTrue(info['voice'])
            self.assertFalse(info['accent'])

    def test_legacy_library_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            conn = connect()
            path = os.path.join(directory,'sound.wav')
            open(path,'wb').close()
            for sid,label,name,voice in [(437,'Cricket','Dế đêm',1),(307,'Wind','Gió',1),(3,'Speech','Wind speech',0),(4,'Unknown class','Wind unknown',1),(5,None,'Gió old',0),(6,'Explosion','Boom',0),(7,'Toilet flush','Toilet',0)]:
                conn.execute('INSERT INTO sounds(id,source_id,path,name,kind,duration,heard_label,heard_score,voice) VALUES(?,1,?,?,?,30,?,.9,?)',(sid,path+str(sid),name,'sfx',label,voice))
                open(path+str(sid),'wb').close()
            conn.commit()
            before = [tuple(r) for r in conn.execute('SELECT * FROM sounds')]
            with mock.patch.object(sound_ai,'hear',side_effect=AssertionError('Không nghe lại')):
                self.assertEqual(ambience.choose(conn,{'time':'night'})['id'],437)
                self.assertEqual(ambience.choose(conn,{'weather':'fog'})['id'],307)
                self.assertEqual([r['id'] for r in sfx_plan.catalog(conn)],[6])
                conn.execute('DELETE FROM sounds WHERE id IN (307,437)')
                self.assertEqual(ambience.choose(conn,{'weather':'fog'})['id'],5)
                conn.execute('DELETE FROM sounds WHERE id=5')
                self.assertIsNone(ambience.choose(conn,{'weather':'fog'}))
            self.assertEqual([tuple(r) for r in conn.execute('SELECT * FROM sounds')], [r for r in before if r[0] not in (307,437,5)])
            conn.close()

    def test_migration_keeps_old_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory,'old.sqlite')
            conn = connect(path)
            conn.execute("INSERT INTO sounds(source_id,path,name,kind,voice,heard_label,heard_score) VALUES(1,'x','Dế','sfx',1,'Cricket',.9)")
            conn.commit()
            if 'accent' in {r['name'] for r in conn.execute('PRAGMA table_info(sounds)')}:
                conn.execute('ALTER TABLE sounds DROP COLUMN accent')
            conn.close()
            conn = connect(path)
            row = conn.execute('SELECT voice,heard_label,heard_score,accent FROM sounds').fetchone()
            self.assertEqual(tuple(row),(1,'Cricket',.9,None))
            conn.close()

    def test_new_listen_instrument_label_and_rejected_sound_are_never_a_bed(self):
        """Rà gộp Đ12v1 (12/10): a NEW listen sets voice=0 for every non-human label — 'Wind instrument…' (a flute) matched 'wind' and
        became the fog bed; a sound the Kho review rejected was offered as a bed too."""
        from core import kho_review
        with tempfile.TemporaryDirectory() as directory:
            conn = connect()
            rows = [(11, 'Wind instrument, woodwind instrument', 'Flute spooky', 0, 0), (12, 'Wind', 'Gio rung', 0, 0),
                    (13, 'Wind', 'Gio dai hon', 0, 0)]
            for sid, label, name, voice, accent in rows:
                p = os.path.join(directory, f'{sid}.wav'); open(p, 'wb').close()
                conn.execute('INSERT INTO sounds(id,source_id,path,name,kind,duration,heard_label,heard_score,voice,accent) '
                             'VALUES(?,1,?,?,?,?,?,.9,?,?)', (sid, p, name, 'sfx', 30 + sid, label, voice, accent))
            conn.commit()
            self.assertEqual(ambience.choose(conn, {'weather': 'fog'})['id'], 13)        # the longest real wind
            kho_review.reject(conn, 'sound', 13, 'thử')
            self.assertEqual(ambience.choose(conn, {'weather': 'fog'})['id'], 12)        # rejected one skipped; the flute never
            kho_review.reject(conn, 'sound', 12, 'thử')
            self.assertIsNone(ambience.choose(conn, {'weather': 'fog'}))
            conn.close()

