retract_dist = 8    # Find from T0 retract dist



# gcode_path = sys.argv[-1]
gcode_path = "C:\\Users\\dhilu\\Documents\\Anisoprint\\test.gcode"

with open(gcode_path, "r", encoding="utf-8", errors="ignore") as f:
    data = f.readlines()

i = 0
layer_num = 0
perimeter_count = 0
perimeter_end = 0
move_perimeter = False
while i < len(data)-5:
    line = data[i]

    # New layer, reset perimeter flag
    if line.startswith(";LAYER_NUM:"):
        layer_num = int(line.split(":")[1].replace("\n", ""))
        perimeter_count = 0
        move_perimeter = False
    
    # First perimeter seen
    if line.startswith(";TYPE:External perimeter"):
        perimeter_count += 1

    # End of first perimeter, keep track of this position to move subsequent perimeter moves here
    if perimeter_count == 1 and line.startswith(";TYPE:") and not line.startswith(";TYPE:External perimeter"):
        perimeter_end = i-1
        # data.insert(perimeter_end, ";thingy go here\n")
        # i += 1                                                  # Increment by one to account for data insert
    
    if perimeter_count > 0:                                     # Perimeter count is incremented after this check, so this is true for subsequent perimeters
        # Find subsequent perimeters and change to perimeter move state
        if data[i+5].startswith(";TYPE:External perimeter"):
            move_perimeter = True

            # data.insert(i, ";thingy come from here\n")
            # i += 1                                              # Increment by one to account for data insert
        
        if move_perimeter:
            # End perimeter move state
            # CASE 1: Hop before next printer move
            if line.startswith(f"G1 E-{retract_dist}") and not data[i+5].startswith(";TYPE:External perimeter"):    # Check that this isn't the start of an external perimeter
                move_perimeter = False
                # data.insert(i, ";thingy end here\n")
                # i += 1                                          # Increment by one to account for data insert
                continue
            
            # CASE 2: No hop
            if data[i+1].startswith(";TYPE:") and not data[i+1].startswith(";TYPE:External perimeter"):
                move_perimeter = False
                # data.insert(i, ";thingy end here\n")
                # i += 1                                          # Increment by one to account for data insert
                continue

            # Move perimeter move to end of first perimeter
            data.insert(perimeter_end, data.pop(i))
            perimeter_end += 1
    i += 1




with open(gcode_path, "w", encoding="utf-8", errors="ignore") as f:
    f.writelines(data)