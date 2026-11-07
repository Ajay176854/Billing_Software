col_starts = [1, 139, 278]

lines = ["SIZE 50 mm, 100 mm", "GAP 2 mm, 0 mm", "DIRECTION 0", "DENSITY 11", "CLS"]

for col_idx in range(3):
    col_x = col_starts[col_idx]
    
    # Part 1 (Top Section: Y = 25 to 175) - Bold Font 2
    # Product Name
    lines.append(f'TEXT {col_x + 95},25,"2",90,1,1,"24K GOLD RING"')
    # Weight / Brand
    lines.append(f'TEXT {col_x + 65},25,"2",90,1,1,"wt. 2.5gm"')
    # Price
    lines.append(f'TEXT {col_x + 35},25,"2",90,1,1,"Rs. 26900/-"')
    
    # Dashed fold line at Y = 180
    for dx in range(col_x + 6, col_x + 98, 12):
        lines.append(f"BAR {dx},180,6,2")
        
    # Part 2 (Bottom Section: Y = 195 to 335) - Full size barcode
    lines.append(f'BARCODE {col_x + 85},195,"128",50,0,90,2,4,"94685000"')
    lines.append(f'TEXT {col_x + 25},215,"2",90,1,1,"94685000"')

lines.append("PRINT 1")
print("\n".join(lines))

