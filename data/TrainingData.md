# Training and Test Data Split

Generated on: 2025-09-24
Total PDFs: 93
Training Set: 80 PDFs
Test Set: 13 PDFs

## Test Set (13 PDFs)
These PDFs should be kept aside for testing and not included in the pre-embedded training data:

1. Crochet Marl Shawl -US2.0.pdf
2. Knitboop_Bojagi.pdf
3. Trolls Ear Saver (UK).pdf
4. Ribbed Bag of Many Things -- August 21, 2020.pdf
5. LosCabosSkinnyWrapFINAL.pdf
6. Chevron Stitch Hood and Scarf --  Low-Vision-Screen-Reader -- September 18, 2020.pdf
7. Shinysuperhero_Tokki.pdf
8. ConsummateV_Final.pdf
9. Knitboop_AccidentalAdventure.pdf
10. TinaTse_LNYKnitDecorations.pdf
11. Whirlpool Cowl - Full.pdf
12. Dingle hat_3 colors_EN.pdf
13. Penuche Twist Socks.pdf

## Training Set (80 PDFs)
These PDFs will be pre-embedded and stored in the embeddings cache:

1. Birdseed Español FINAL.pdf
2. Knitboop_Mathematical!Shawl.pdf
3. Harry Potter Ear Saver (UK).pdf
4. Knitboop_Doldam.pdf
5. Kitty Ankle Socks.pdf
6. Madeleva Moebius Cowl_FINAL3.pdf
7. Callatis crescent shawl crochet pattern Andrea Cretu 2019.pdf
8. Free Range Cables.pdf
9. Sunshine_Patch.pdf
10. Baby Yoda Ear Saver (UK).pdf
11. Knitboop_NamuSweater.pdf
12. Subtlism_Scarf_V1.pdf
13. Roller Skate Crochet Pattern v2.pdf
14. Spiderweb hexagon -US2.0.pdf
15. Tiilda Mittens_Isang.pdf
16. Eye of the Helix Socks.pdf
17. simple_flower_tutorial (1).pdf
18. Hideaway Cowl.pdf
19. SultanDyes_Dragons EyeHat.pdf
20. TinaTse_BalancingTextureScarf.pdf
21. Ribbed Bag of Many Things Low-Vision-Screen-Reader -- August 21, 2020.pdf
22. Cakes Two to Tango-FR2.1.pdf
23. Spelunkin Cowl.pdf
24. Trolls Ear Saver.pdf
25. Animal Crossing Fossil Pillow crochet pattern v3.pdf
26. Shinysuperhero_TheFabBall.pdf
27. 2019 CROCHET_Anemone Cowl_Digital Download_2.0.pdf
28. Between the Lines Cardigan by Tina Tse.pdf
29. HiddenFalls Headband_FINAL.pdf
30. Shield-Shaped Pill (Lamictal) Crochet Pattern v2.pdf
31. In waves baby blanket crochet pattern Andrea Cretu 2019.pdf
32. Baby Yoda Ear Saver.pdf
33. TwistHeadWarmer PatternV4_Spanish.pdf
34. Knitboop_YeonSweater.pdf
35. Rose_Apothecary_Full_Size.pdf
36. Jute_Pot_Cosy.pdf
37. 10.1.21_Knot Your Mamas Headband.pdf
38. SultanDyes_TrotOutCowl.pdf
39. Port Hole Scarf.pdf
40. Lets start a riot blanket- US.pdf
41. Dingle hat_2 colors_EN.pdf
42. Cherry Blossom Crochet Pattern v2.pdf
43. Hipstamatic.pdf
44. Mask Ear Protector.pdf
45. TwistHeadWarmer PatternV4.pdf
46. The Sienna Headband.pdf
47. Teenie_tiny_bunting.pdf
48. Knitboop_Lily.pdf
49. Not The Last Cowl_V1.pdf
50. Harry Potter Ear Saver.pdf
51. Pine cross summer top crochet pattern Andrea Cretu 2021.pdf
52. Cakes Two to Tango-NL2.0.pdf
53. ThrowbackThrow PatternV3.pdf
54. Mountains and Valleys Scarf.pdf
55. Dingle hat_5 colors_EN.pdf
56. The Shrouds of Sirius_2 pgs.pdf
57. Knitboop_Namu.pdf
58. birdseed.pdf
59. IneseSang_Migla.pdf
60. Tokki - DANSK.pdf
61. Chevron Stitch Hood and Scarf -- September 18, 2020.pdf
62. Tincture_Full_Size.pdf
63. Knitboop_Bom.pdf
64. Mask Ear Protector (UK).pdf
65. Parchment_and_Pressed_Flowers_Full_Size.pdf
66. Uniquely Yours Shawl Final 1.pdf
67. Droplets of Starlight Cowl_2pg.pdf
68. v1.2_Seashell Cowl_Full Color.pdf
69. Tiilda Hat_Isang.pdf
70. The Newcomer Hat.pdf
71. Chex Cowl.pdf
72. Knitboop_Hanok.pdf
73. 20180909_Winter Libations Hat Pattern bigger.pdf
74. SultanDyes_Castonides AntidoteSocks.pdf
75. TinaTse_CablesWithATwistEarwarmers.pdf
76. Cakes Two to Tango-US2.pdf
77. Dingle hat_4 colors_EN.pdf
78. TwistHeadWarmer PatternV4_French.pdf
79. Knitboop_Malus.pdf
80. Seed Stitch Scarf.pdf

## Usage Instructions

1. The training set PDFs should be processed through the offline ingestion script to generate embeddings
2. These embeddings will be saved to `./embeddings/` directory (gitignored due to size)
3. Each database implementation will load from this cache rather than re-computing
4. The test set PDFs should be used for:
   - Testing real-time embedding generation through the web interface
   - Evaluating cross-document search quality
   - Measuring performance on unseen documents