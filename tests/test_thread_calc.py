"""Tests for thread estimation calculations."""

import pytest

from xstitchlab.core.thread_calc import (
    ThreadCalculator,
    ThreadEstimate,
    quick_estimate,
    DMC_SKEIN_LENGTH_METERS,
)
from xstitchlab.core.pattern import (
    Pattern,
    PatternMetadata,
    ColorLegendEntry,
    DMCColor,
)


class TestThreadCalculator:
    """Tests for ThreadCalculator class."""

    @pytest.fixture
    def calculator(self):
        """Create a standard calculator."""
        return ThreadCalculator(fabric_count=14)

    @pytest.fixture
    def simple_pattern(self):
        """Create a simple test pattern."""
        grid = [[0] * 10 for _ in range(10)]  # 100 stitches of color 0
        legend = [
            ColorLegendEntry(
                dmc_color=DMCColor("310", "Black", (0, 0, 0)),
                symbol="●",
                stitch_count=100
            )
        ]
        pattern = Pattern(grid=grid, legend=legend)
        pattern.count_stitches()
        return pattern

    def test_thread_length_calculation(self, calculator):
        """Test basic thread length calculation."""
        length_cm, length_m = calculator.calculate_thread_length(100)

        # 100 stitches * 2.5cm * 1.2 (wastage) = 300cm = 3m
        assert abs(length_cm - 300) < 1
        assert abs(length_m - 3) < 0.1

    def test_skein_calculation(self, calculator):
        """Test skein calculation."""
        # 8 meters per skein
        skeins_whole, skeins_decimal = calculator.calculate_skeins(16)

        assert skeins_whole == 2
        assert abs(skeins_decimal - 2.0) < 0.01

    def test_skein_calculation_partial(self, calculator):
        """Test skein calculation with partial skein."""
        skeins_whole, skeins_decimal = calculator.calculate_skeins(10)

        assert skeins_whole == 2  # Rounded up from 1.25
        assert abs(skeins_decimal - 1.25) < 0.01

    def test_estimate_color(self, calculator):
        """Test estimating thread for a single color."""
        estimate = calculator.estimate_color("310", "Black", 1000)

        assert estimate.dmc_code == "310"
        assert estimate.stitch_count == 1000
        assert estimate.thread_length_cm > 0
        assert estimate.skeins_needed >= 1

    def test_estimate_pattern(self, calculator, simple_pattern):
        """Test estimating thread for entire pattern."""
        estimates = calculator.estimate_pattern(simple_pattern)

        assert len(estimates) == 1
        assert estimates[0].dmc_code == "310"
        assert estimates[0].stitch_count == 100

    def test_different_fabric_counts(self):
        """Test that different fabric counts affect thread usage."""
        calc_14 = ThreadCalculator(fabric_count=14)
        calc_18 = ThreadCalculator(fabric_count=18)

        length_14, _ = calc_14.calculate_thread_length(100)
        length_18, _ = calc_18.calculate_thread_length(100)

        # 18-count uses less thread per stitch
        assert length_18 < length_14

    def test_wastage_factor(self):
        """Test wastage factor affects calculations."""
        calc_low = ThreadCalculator(wastage_factor=0.1)
        calc_high = ThreadCalculator(wastage_factor=0.3)

        length_low, _ = calc_low.calculate_thread_length(100)
        length_high, _ = calc_high.calculate_thread_length(100)

        assert length_high > length_low

    def test_half_stitch_uses_less_thread(self):
        """Test that half stitches use less thread."""
        calc_full = ThreadCalculator(stitch_type="full_cross")
        calc_half = ThreadCalculator(stitch_type="half")

        length_full, _ = calc_full.calculate_thread_length(100)
        length_half, _ = calc_half.calculate_thread_length(100)

        assert length_half < length_full


class TestEstimateAll:
    """Tests for estimate_all output format."""

    @pytest.fixture
    def multi_color_pattern(self):
        """Create a pattern with multiple colors."""
        grid = [
            [0, 1, 2],
            [1, 2, 0],
            [2, 0, 1]
        ]
        legend = [
            ColorLegendEntry(
                dmc_color=DMCColor("White", "White", (255, 255, 255)),
                symbol="○",
                stitch_count=3
            ),
            ColorLegendEntry(
                dmc_color=DMCColor("310", "Black", (0, 0, 0)),
                symbol="●",
                stitch_count=3
            ),
            ColorLegendEntry(
                dmc_color=DMCColor("321", "Christmas Red", (199, 43, 59)),
                symbol="★",
                stitch_count=3
            ),
        ]
        pattern = Pattern(grid=grid, legend=legend)
        pattern.count_stitches()
        return pattern

    def test_estimate_all_format(self, multi_color_pattern):
        """Test estimate_all returns correct format."""
        calc = ThreadCalculator()
        estimates = calc.estimate_all(multi_color_pattern)

        assert len(estimates) == 3

        for est in estimates:
            assert "dmc_code" in est
            assert "name" in est
            assert "stitch_count" in est
            assert "meters" in est
            assert "skeins" in est


class TestShoppingList:
    """Tests for shopping list generation."""

    @pytest.fixture
    def pattern(self):
        """Create a test pattern."""
        grid = [[0] * 50 for _ in range(50)]  # 2500 stitches
        legend = [
            ColorLegendEntry(
                dmc_color=DMCColor("310", "Black", (0, 0, 0)),
                symbol="●",
                stitch_count=2500
            )
        ]
        pattern = Pattern(grid=grid, legend=legend)
        pattern.metadata.title = "Test Pattern"
        pattern.count_stitches()
        return pattern

    def test_shopping_list_content(self, pattern):
        """Test shopping list contains expected information."""
        calc = ThreadCalculator(fabric_count=14)
        shopping_list = calc.get_shopping_list(pattern)

        assert "Test Pattern" in shopping_list
        assert "310" in shopping_list
        assert "Black" in shopping_list
        assert "14-count" in shopping_list


class TestQuickEstimate:
    """Tests for quick_estimate function."""

    def test_quick_estimate(self):
        """Test quick_estimate function."""
        grid = [[0] * 40 for _ in range(40)]
        legend = [
            ColorLegendEntry(
                dmc_color=DMCColor("310", "Black", (0, 0, 0)),
                symbol="●",
                stitch_count=1600
            )
        ]
        pattern = Pattern(grid=grid, legend=legend)
        pattern.count_stitches()

        summary = quick_estimate(pattern, fabric_count=14)

        assert summary["color_count"] == 1
        assert summary["total_stitches"] == 1600
        assert summary["total_skeins"] >= 1
        assert summary["fabric_count"] == 14
