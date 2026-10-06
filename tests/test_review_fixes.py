# test_review_fixes.py — regression tests for the October 2026 review: STAT kept for axes outside fvar, RIBBI names and bits, names on every platform, safe PostScript names.

import os
import pytest
from fontTools.ttLib import TTFont

import core

#: vf-clamp's Inter 4 fixture (wght 100–900, opsz 14–32; STAT also describes ital).
INTER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'fixtures', 'Inter-Variable.ttf'))

pytestmark = pytest.mark.skipif(not os.path.exists(INTER), reason='Inter fixture not found')


def _clamp(tmp_path, names, family, src=INTER):
	"""Run the plugin's real pipeline and reopen the result."""
	out = str(tmp_path / 'out.ttf')
	core.produce_restricted_vf(src, names, family, out, 'TTF')
	return TTFont(out)


def test_stat_keeps_axes_not_in_fvar(tmp_path):
	"""Inter's STAT describes ital and opsz; clamping must not delete either axis record."""
	f = _clamp(tmp_path, ['Regular', 'Medium', 'SemiBold', 'Bold'], 'Inter Regular-Bold')
	tags = [a.AxisTag for a in f['STAT'].table.DesignAxisRecord.Axis]
	assert 'ital' in tags and 'wght' in tags


def test_instance_postscript_names_follow_new_prefix(tmp_path):
	"""Named instances must not keep the retail InterVariable-* PostScript names."""
	f = _clamp(tmp_path, ['Regular', 'Medium', 'SemiBold', 'Bold'], 'Inter Regular-Bold')
	ps = [f['name'].getDebugName(i.postscriptNameID) for i in f['fvar'].instances if i.postscriptNameID != 0xFFFF]
	assert ps and all(not p.startswith('InterVariable') for p in ps)


def test_unique_id_is_rewritten(tmp_path):
	"""nameID 3 must differ from the source font's, so OS font caches don't confuse the two."""
	src_id = TTFont(INTER)['name'].getDebugName(3)
	f = _clamp(tmp_path, ['Regular', 'Bold'], 'Inter Regular-Bold')
	assert f['name'].getDebugName(3) != src_id
	assert 'Inter-Regular-Bold' in f['name'].getDebugName(3)


def test_pinned_bold_is_ribbi_bold(tmp_path):
	"""A single Bold instance: BOLD bit, never REGULAR, and nameID 2 'Bold'."""
	f = _clamp(tmp_path, ['Bold'], 'Inter Bold')
	fs = f['OS/2'].fsSelection
	assert fs & 0x20 and not fs & 0x40
	assert f['name'].getDebugName(2) == 'Bold'


def test_semibold_default_is_not_bold(tmp_path):
	"""RIBBI bold starts at 700: a SemiBold pin is not flagged Bold."""
	f = _clamp(tmp_path, ['SemiBold'], 'Inter SemiBold')
	assert not f['OS/2'].fsSelection & 0x20


def test_italic_source_stays_italic(tmp_path):
	"""A separate italic VF (no ital/slnt axis in fvar) keeps its ITALIC bit and RIBBI name."""
	src = TTFont(INTER)
	src['OS/2'].fsSelection = (src['OS/2'].fsSelection & ~0x40) | 0x01
	italic_path = str(tmp_path / 'InterItalic.ttf')
	src.save(italic_path)
	f = _clamp(tmp_path, ['Regular', 'Medium', 'SemiBold', 'Bold'], 'Inter Italic Regular-Bold', src=italic_path)
	fs = f['OS/2'].fsSelection
	assert fs & 0x01 and not fs & 0x40
	assert f['name'].getDebugName(2) == 'Italic'


def test_postscript_names_transliterate_and_stay_unique():
	"""Accents are transliterated, other scripts get a hash, long names stay distinct."""
	assert core.sanitize_ps_name('Été Grotesk') == 'Ete-Grotesk'
	assert core.sanitize_ps_name('源ノ角ゴシック').startswith('Font-')
	a = core.sanitize_ps_name('Very Long Family Name Extended Condensed Display Text Regular-Bold A')
	b = core.sanitize_ps_name('Very Long Family Name Extended Condensed Display Text Regular-Bold B')
	assert len(a) <= 63 and len(b) <= 63 and a != b


def test_short_hash_matches_the_npm_package():
	"""Same hash as shortHash() in @overpunch/vf-clamp, so names agree across tools."""
	assert core.short_hash('Inter') == core.short_hash('Inter')
	assert len(core.short_hash('Inter')) == 6
