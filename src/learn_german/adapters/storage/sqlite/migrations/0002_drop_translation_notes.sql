-- The translation note kind no longer exists (decision 0049). Its records would not parse
-- as a NoteKind, and a chunk's status now depends on its transformation note alone.

DELETE FROM pushed_notes WHERE note_kind = 'translation';
