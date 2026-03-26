"""
Unit tests for app/dashboard/calculations.py
Covers TEST-02 through TEST-06.
"""
import sys
import os
import pytest
import pandas as pd
import numpy as np

# Make 'calculations' importable without triggering streamlit
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'dashboard'))

from calculations import (
    calcular_curva_aprendizado,
    calcular_dias_uteis,
    colorir_status,
    normalizar_id_historia,
    parse_data_criacao,
    classificar_subtarefa,
    projetar_burndown,
)


# ── TEST-02: calcular_curva_aprendizado ──────────────────────────────────────

class TestCalcularCurvaAprendizado:
    def test_returns_two_lists_same_length(self):
        datas, valores = calcular_curva_aprendizado(
            pd.Timestamp('2026-01-01'), pd.Timestamp('2026-03-31'), total=100
        )
        assert len(datas) > 0
        assert len(datas) == len(valores)

    def test_sigmoid_first_value_near_zero(self):
        datas, valores = calcular_curva_aprendizado(
            pd.Timestamp('2026-01-01'), pd.Timestamp('2026-03-31'), total=100
        )
        assert valores[0] < 5  # well below total at start

    def test_sigmoid_last_value_near_total(self):
        datas, valores = calcular_curva_aprendizado(
            pd.Timestamp('2026-01-01'), pd.Timestamp('2026-03-31'), total=100
        )
        assert valores[-1] > 95  # near total at end

    def test_sigmoid_monotonically_increasing(self):
        datas, valores = calcular_curva_aprendizado(
            pd.Timestamp('2026-01-01'), pd.Timestamp('2026-06-30'), total=50
        )
        for i in range(1, len(valores)):
            assert valores[i] >= valores[i - 1], f"Not monotonic at index {i}"

    def test_nat_start_returns_empty(self):
        datas, valores = calcular_curva_aprendizado(pd.NaT, pd.Timestamp('2026-03-31'), total=100)
        assert datas == []
        assert valores == []

    def test_nat_end_returns_empty(self):
        datas, valores = calcular_curva_aprendizado(pd.Timestamp('2026-01-01'), pd.NaT, total=100)
        assert datas == []
        assert valores == []

    def test_zero_total_returns_empty(self):
        datas, valores = calcular_curva_aprendizado(
            pd.Timestamp('2026-01-01'), pd.Timestamp('2026-03-31'), total=0
        )
        assert datas == []
        assert valores == []

    def test_single_day_range_returns_two_points(self):
        # n < 2 case: same day start and end
        datas, valores = calcular_curva_aprendizado(
            pd.Timestamp('2026-01-01'), pd.Timestamp('2026-01-01'), total=10
        )
        assert len(datas) == 2
        assert valores == [0, 10]


# ── TEST-03: calcular_dias_uteis ─────────────────────────────────────────────

class TestCalcularDiasUteis:
    def test_monday_to_friday_same_week(self):
        # Mon→Fri exclusive start: counts Tue Wed Thu Fri = 4
        result = calcular_dias_uteis(
            pd.Timestamp('2026-03-23'),  # Monday
            pd.Timestamp('2026-03-27'),  # Friday
        )
        assert result == 4

    def test_friday_to_monday_next_week(self):
        # Fri→Mon: counts only Mon = 1
        result = calcular_dias_uteis(
            pd.Timestamp('2026-03-20'),  # Friday
            pd.Timestamp('2026-03-23'),  # Monday
        )
        assert result == 1

    def test_same_day_returns_zero(self):
        result = calcular_dias_uteis(
            pd.Timestamp('2026-03-23'),
            pd.Timestamp('2026-03-23'),
        )
        assert result == 0

    def test_fim_before_inicio_returns_zero(self):
        result = calcular_dias_uteis(
            pd.Timestamp('2026-03-27'),
            pd.Timestamp('2026-03-23'),
        )
        assert result == 0

    def test_nat_start_returns_zero(self):
        assert calcular_dias_uteis(pd.NaT, pd.Timestamp('2026-03-27')) == 0

    def test_nat_end_returns_zero(self):
        assert calcular_dias_uteis(pd.Timestamp('2026-03-23'), pd.NaT) == 0

    def test_weekend_skipped(self):
        # Friday to next Monday = 1 business day (only Monday counts, exclusive start)
        result = calcular_dias_uteis(
            pd.Timestamp('2026-03-20'),  # Friday
            pd.Timestamp('2026-03-23'),  # Monday
        )
        assert result == 1  # Saturday and Sunday skipped


# ── TEST-04: colorir_status ──────────────────────────────────────────────────

class TestColoriStatus:
    @pytest.mark.parametrize("status", ['Done', 'Closed', 'Resolved', 'Concluído', 'Concluida'])
    def test_done_statuses_return_green(self, status):
        result = colorir_status(status)
        assert '#90EE90' in result

    def test_in_progress_returns_blue(self):
        assert '#87CEEB' in colorir_status('In Progress')

    def test_to_do_returns_orange(self):
        assert '#FFE4B5' in colorir_status('To Do')

    def test_backlog_returns_gray(self):
        assert '#D3D3D3' in colorir_status('Backlog')

    @pytest.mark.parametrize("status", ['Canceled', 'Cancelled', 'Cancelado'])
    def test_cancelled_statuses_return_gold(self, status):
        assert '#FFD700' in colorir_status(status)

    def test_unknown_returns_empty_string(self):
        assert colorir_status('UNKNOWN_STATUS') == ''

    def test_empty_string_returns_empty(self):
        assert colorir_status('') == ''


# ── TEST-05: classificar_subtarefa ───────────────────────────────────────────

class TestClassificarSubtarefa:
    def test_story_bug_pattern(self):
        assert classificar_subtarefa('implementar Story Bug correção') == 'Story Bug'

    def test_story_bug_case_insensitive(self):
        assert classificar_subtarefa('STORY BUG fix') == 'Story Bug'

    def test_story_bug_no_space(self):
        assert classificar_subtarefa('storybug') == 'Story Bug'

    def test_rn_fmk_pattern(self):
        assert classificar_subtarefa('regra RN-FMK validacao') == 'RN-FMK'

    def test_rn_pattern(self):
        assert classificar_subtarefa('implementar RN negocio') == 'RN'

    def test_rn_not_matched_inside_word(self):
        # 'CRNT' contains 'RN' but not as whole word — should be Desenvolvimento
        result = classificar_subtarefa('CRNT implementation')
        assert result == 'Desenvolvimento/Outros'

    def test_default_classification(self):
        assert classificar_subtarefa('desenvolvimento tela login') == 'Desenvolvimento/Outros'

    def test_none_returns_default(self):
        assert classificar_subtarefa(None) == 'Desenvolvimento/Outros'

    def test_rn_fmk_takes_priority_over_rn(self):
        # RN-FMK contains RN but should match Story Bug check first only if STORY BUG present
        # RN-FMK check comes before plain RN
        assert classificar_subtarefa('RN-FMK rule') == 'RN-FMK'


# ── TEST-05b: normalizar_id_historia ────────────────────────────────────────

class TestNormalizarIdHistoria:
    def test_none_returns_none(self):
        assert normalizar_id_historia(None) is None

    def test_nat_returns_none(self):
        assert normalizar_id_historia(pd.NaT) is None

    def test_strips_brackets(self):
        assert normalizar_id_historia('[PROJ-10]') == 'PROJ-10'

    def test_uppercases(self):
        assert normalizar_id_historia('proj-10') == 'PROJ-10'

    def test_normalises_spaced_hyphen(self):
        assert normalizar_id_historia('PROJ - 10') == 'PROJ-10'

    def test_normalises_trailing_hyphen_space(self):
        assert normalizar_id_historia('PROJ- 10') == 'PROJ-10'

    def test_normalises_leading_space_hyphen(self):
        assert normalizar_id_historia('PROJ -10') == 'PROJ-10'

    def test_collapses_extra_spaces(self):
        result = normalizar_id_historia('PROJ  -  10')
        assert '-' in result
        assert '  ' not in result


# ── TEST-05c: parse_data_criacao ─────────────────────────────────────────────

class TestParseDataCriacao:
    def test_none_returns_nat(self):
        assert pd.isna(parse_data_criacao(None))

    def test_empty_string_returns_nat(self):
        assert pd.isna(parse_data_criacao(''))

    def test_iso_no_tz(self):
        result = parse_data_criacao('2026-01-15T09:00:00')
        assert result == pd.Timestamp('2026-01-15 09:00:00')

    def test_br_format(self):
        result = parse_data_criacao('15/01/2026')
        assert result == pd.Timestamp('2026-01-15')

    def test_standard_datetime_format(self):
        result = parse_data_criacao('2026-01-15 09:00:00')
        assert result == pd.Timestamp('2026-01-15 09:00:00')


# ── TEST-06: projetar_burndown ───────────────────────────────────────────────

class TestProjetarBurndown:
    BASE_ARGS = dict(
        historias_faltantes=4.0,
        total_planejado=10.0,
        realizado_atual=6.0,
        ultima_data_real_bh=pd.Timestamp('2026-03-01'),
    )

    def test_returns_nonempty_on_valid_input(self):
        datas, valores = projetar_burndown(
            ritmo=2.0, prazo_limite=pd.NaT, **self.BASE_ARGS
        )
        assert len(datas) > 0
        assert len(datas) == len(valores)

    def test_last_value_equals_total_planejado(self):
        datas, valores = projetar_burndown(
            ritmo=2.0, prazo_limite=pd.NaT, **self.BASE_ARGS
        )
        assert valores[-1] == pytest.approx(10.0)

    def test_zero_ritmo_returns_empty(self):
        datas, valores = projetar_burndown(
            ritmo=0, prazo_limite=pd.NaT, **self.BASE_ARGS
        )
        assert datas == []
        assert valores == []

    def test_negative_ritmo_returns_empty(self):
        datas, valores = projetar_burndown(
            ritmo=-1.0, prazo_limite=pd.NaT, **self.BASE_ARGS
        )
        assert datas == []
        assert valores == []

    def test_optimistic_finishes_faster_than_base(self):
        base_datas, _ = projetar_burndown(ritmo=2.0, prazo_limite=pd.NaT, **self.BASE_ARGS)
        fast_datas, _ = projetar_burndown(ritmo=2.0 * 1.3, prazo_limite=pd.NaT, **self.BASE_ARGS)
        assert len(fast_datas) <= len(base_datas)

    def test_pessimistic_finishes_slower_than_base(self):
        base_datas, _ = projetar_burndown(ritmo=2.0, prazo_limite=pd.NaT, **self.BASE_ARGS)
        slow_datas, _ = projetar_burndown(ritmo=2.0 * 0.7, prazo_limite=pd.NaT, **self.BASE_ARGS)
        assert len(slow_datas) >= len(base_datas)

    def test_prazo_limite_truncates_series(self):
        # prazo_limite 1 day after start — should stop early
        prazo = pd.Timestamp('2026-03-02')
        datas, valores = projetar_burndown(
            ritmo=0.5, prazo_limite=prazo, **self.BASE_ARGS
        )
        if datas:
            assert datas[-1] <= prazo
