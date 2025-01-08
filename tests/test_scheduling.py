from scheduling.schedule_matches import schedule_match

# Test scheduling
result = schedule_match("LOS GRINGOS", "SCHOOL SHOOTERS")
if result:
    print("Match scheduled successfully!")
else:
    print("Match scheduling failed.")
