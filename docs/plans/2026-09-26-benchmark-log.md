# Benchmark log

Append-only record of recipe tuning against `tools/benchmark.py` (`exact` = fraction of
cells whose DMC code matches the committed final; fabric-vs-fabric counts as a match).
One row per attempt. "pre(W)" = `quantize_image kmeans n_colors=8` + `pixelate width=W
majority steps=1`; "cleanup" = remove_isolated, fill_holes, snap_diagonals, connect_lines,
rectangularize; "sub A→B" = substitute_colour; "merge A→B" = merge_colours; "bg auto" =
background_to_fabric auto; "outline auto" = outline_to_backstitch auto.

Thresholds in `tests/test_benchmark.py` = final score − 0.02, floored to two decimals.

## 2026-09-26 — Task 6, first tuning pass

| Design | Recipe | exact | Note |
|---|---|---|---|
| Riga | pre(45) + cleanup (predesigned default) | 0.8889 | starting point |
| Riga | pre(45), no cleanup | 0.9062 | every cleanup op hurts here |
| Riga | pre(45) + remove_isolated only | 0.8983 | |
| Riga | pre(45) + fill_holes only | 0.8958 | |
| Riga | pre(45) + snap_diagonals only | 0.9037 | |
| Riga | pre(45) + connect_lines only | 0.9027 | |
| Riga | pre(45) + rectangularize only | 0.9007 | |
| Riga | pre(45) n_colors=7 | 0.8212 | loses 3865 (white house) |
| Riga | pre(45) n_colors=9 | 0.8998 | |
| Riga | pre(45) n_colors=10 | 0.9002 | |
| Riga | pre(45) color_space=rgb | 0.4030 | sky maps to 747, green to 3053 |
| Riga | quantize + pixelate sample=nearest | 0.8128 | |
| Riga | median_cut 8 + pixelate 45 | 0.4805 | only 6 colours survive |
| Riga | pre(45) + generate_backstitch 80 | 0.9062 | **final**; 285 segments vs 212 in final. Remaining diffs are hand edits (windows squared, gable edges, door) |
| Lübeck | pre(70) + cleanup + bg auto + crop_pad 50×50 fit_content | 0.9244 | starting point |
| Lübeck | same, no cleanup | 0.9280 | |
| Lübeck | + sub 357→3777 | 0.9536 | research's legend swap |
| Lübeck | + merge 357→3777 | error | 3777 not in legend: substitute, not merge |
| Lübeck | n_colors=7 + sub 357→3777 | 0.9428 | 842 becomes 3782 |
| Lübeck | n_colors=9 + sub 357→3777 | 0.9396 | |
| Lübeck | + sub 357→3777 + merge 519→813 | 0.9540 | 519 is a one-cell stray; 7/7 colours |
| Lübeck | single cleanup ops on top (remove_isolated / fill_holes / snap / connect / rectangularize) | 0.9508 / 0.9472 / 0.9536 / 0.9532 / 0.9500 | none helps |
| Lübeck | + sub 813→White + generate_backstitch 80 | 0.9540 | **final**; fabric named as in the final, 193 segments |
| Tallinn | pre(50) + cleanup + bg auto + outline auto | 0.9004 | starting point |
| Tallinn | same, no cleanup | 0.8956 | cleanup helps slightly here |
| Tallinn | n_colors=7 | 0.7640 | 613/822 collapse into 3047 |
| Tallinn | n_colors=9 | 0.8900 | |
| Tallinn | bg auto, no outline op | 0.8600 | final dissolved most of the 3371 outline (only 88 cells left) |
| Tallinn | outline keep_cells=true | 0.8700 | |
| Tallinn | single cleanup ops instead of all five | 0.8956–0.8976 | |
| Tallinn | + regularize_repeats | 0.9004 | no change |
| Tallinn | + absorb_small_regions 3 | 0.9028 | +0.002, not worth an op |
| Tallinn | + smooth | 0.9008 | |
| Tallinn | + sub 827→White | 0.9004 | **final**; remaining diffs: window fills kept as 3371 in the final, arcade redrawn |
| Bergen | pre(50) + cleanup | 0.6856 | |
| Bergen | pre(50), no cleanup | 0.6768 | |
| Bergen | pre(55) + crop_pad 50×50 fit_content | 0.6716 | fit_content centres the mountain too |
| Bergen | pre(55) + crop_pad offset (−7,−8) | 0.7652 | research's translation |
| Bergen | offsets (−6,−8) / (−7,−7) / (−8,−8) / (−7,−9) / (−6,−7) | 0.7628 / 0.7500 / 0.7552 / 0.7424 / 0.7312 | (−7,−8) confirmed |
| Bergen | + sub 402→977 | 0.7988 | |
| Bergen | + sub 402→977 + merge 762→3072 | 0.8040 | |
| Bergen | + sub 402→977 + merge 762→White | 0.8164 | 762 is mostly fabric in the final |
| Bergen | single cleanup ops on top | 0.8052–0.8164 | none helps |
| Bergen | n_colors=9 | 0.7452 | (before subs) 402 still spans both red houses |
| Bergen | n_colors=10 | 0.7492 | (before subs) 722 = orange house, 728 = red house, 3858 = mountain: separable |
| Bergen | n_colors=11 / 12 | 0.7400 / 0.5888 | 762 eats the fabric at 12 |
| Bergen | n10 + offset + merge 3768→White + sub 3858→3860 + sub 722→977 + merge 762→White + sub 728→3830 | 0.8656 | |
| Bergen | same + merge 3830→White first (ground strip) | 0.8928 | **final** (+ generate_backstitch 80, 314 segments) |
| Bergen | final + single cleanup ops | 0.8860–0.8956 | ≤ +0.003, not worth an op |
| Gdańsk | pre(50) + cleanup | 0.0176 | sky stitched as 813, whole palette off |
| Gdańsk | pre(50), no cleanup | 0.0208 | |
| Gdańsk | + bg auto | 0.4368 | |
| Gdańsk | + sub 3024→3866, 648→3024, 502→3761 | 0.6604 | order matters: rename 3024 before 648 takes its code |
| Gdańsk | + outline auto | 0.7308 | 310 (446 cells) is a drawn outline; final keeps 10 |
| Gdańsk | same with cleanup | 0.7356 | |
| Gdańsk | n_colors=9 / 10 (bg only) | 0.4368 / 0.4212 | codes shift (762, 739), no new separation |
| Gdańsk | + sub 3790→356, 3031→356, 642→3045 | 0.7828 | |
| Gdańsk | n9 chain / n10 chain | 0.7828 / 0.7808 | |
| Gdańsk | n9 chain, no cleanup | 0.7848 | +0.002 |
| Gdańsk | + regularize_repeats / absorb_small_regions 3 / outline last | 0.7812 / 0.7852 / 0.7828 | |
| Gdańsk | n8, no cleanup, bg + outline + 6 subs + sub 813→B5200 | 0.7828 | **final**; 11 ops. Remaining: fountain/statues removed, windows redrawn, façade simplified by hand |

Final scores and thresholds: Riga 0.9062 (≥ 0.88), Lübeck 0.9540 (≥ 0.93), Bergen 0.8928
(≥ 0.87), Tallinn 0.9004 (≥ 0.88), Gdańsk 0.7828 (≥ 0.76). Bergen and Gdańsk beat the
research ceilings (0.765 / 0.740) because more k-means colours (Bergen) and the outline op
(Gdańsk) recover cells the hand-edit estimate assumed were lost.
