# Changelog: Multiple Program Selection (Max 3)

## Date: February 16, 2026

## Overview
Changed the "Areas of Interest" / "Program Selection" question from single-select (radio buttons) to multi-select with a maximum of 3 selections.

## Changes Made

### 1. Question Definition (`app-test.py` line ~735)
**Changed:**
- Question type from `"select"` to `"multiselect_programs"`
- Prompt from "What exact program do you want to study?" to "What programs are you interested in studying?"
- Help text updated to mention "Select up to 3 programs"
- Added `"max_selections": 3` parameter

### 2. Input Rendering (`app-test.py` line ~1413)
**Added:** New handler for `multiselect_programs` question type
- Uses `st.multiselect()` instead of `st.radio()`
- Enforces `max_selections=3` parameter
- Handles both list and legacy string format for backwards compatibility
- Shows helpful text: "Choose up to 3 programs"

### 3. Validation Logic (`app-test.py` line ~911)
**Updated:** `validate_answer()` function
- Checks if selection is a list
- Validates minimum 1 selection
- Validates maximum 3 selections
- Maintains backwards compatibility with legacy single-string selection

### 4. Profile Update (`app-test.py` line ~994)
**Enhanced:** `update_profile()` function
- Handles list of selected programs
- Merges interest tags from all selected programs
- Removes duplicate tags while preserving order
- Maintains backwards compatibility

### 5. Chat Display (`app-test.py` line ~1148)
**Updated:** `_format_answer_for_chat()` function
- Displays comma-separated list of selected programs
- Handles both list and string formats

### 6. Transition Messages (`app-test.py` line ~1075)
**Updated:** Message wording
- Changed from "Awesome choice!" to "Awesome choices!" (plural)
- Updated message to be more appropriate for multiple selections

### 7. Question Status Check (`app-test.py` line ~863)
**Updated:** `_question_answered()` function
- Checks if list has at least one element
- Maintains backwards compatibility with string format

### 8. Engine Input Conversion (`app-test.py` line ~1279)
**Updated:** `_profile_to_engine_inputs()` function
- Converts `specific_program_interest` to list format for engine
- Ensures backwards compatibility by wrapping single values in list

## Benefits

1. **More Flexible**: Students can express interest in multiple related fields
2. **Better Recommendations**: Engine can match across multiple program areas
3. **Realistic**: Students often have 2-3 programs in mind, not just 1
4. **Better Tags**: Multiple programs = richer set of interest tags for matching

## Backwards Compatibility

All changes maintain backwards compatibility with existing profiles that have single program selections:
- Single string values are automatically wrapped in lists where needed
- Validation and display logic handle both formats
- No data migration required

## User Experience

**Before:**
- User could only select 1 program (radio buttons)
- Had to choose between similar interests

**After:**
- User can select 1-3 programs (multiselect checkboxes)
- Can express multiple interests
- Clear limit shown: "Choose up to 3 programs maximum"
- Validation prevents selecting too many or too few

## Testing Recommendations

1. ✅ Test selecting 1 program (minimum)
2. ✅ Test selecting 3 programs (maximum)
3. ✅ Try to select 4+ programs (should be blocked by `max_selections`)
4. ✅ Test "Save & Continue" with no selection (should show error)
5. ✅ Test chat display shows comma-separated list
6. ✅ Test transition message is appropriate
7. ✅ Test interest tags are properly merged from all selections
8. ✅ Test backwards compatibility with existing single-value profiles

## Example Output

**Chat Display:**
```
You: Digital Marketing & E-commerce, Data Science & Analytics, Software Engineering

Aina: Awesome choices! Digital Marketing & E-commerce, Data Science & Analytics, 
Software Engineering - fantastic fields with strong career prospects. 🚀

Let me gather some details about your academic background next...
```

**Interest Tags Merged:**
- Digital Marketing → ["Business", "Digital Marketing", "Creative"]
- Data Science → ["IT", "Data", "Engineering"]
- Software Engineering → ["IT", "Engineering"]
- **Merged Result:** ["Business", "Digital Marketing", "Creative", "IT", "Data", "Engineering"]

## Technical Notes

- Uses Streamlit's built-in `max_selections` parameter for clean UX
- No need for custom validation of max count in widget
- List comprehension used for tag deduplication: `list(dict.fromkeys(all_tags))`
- All existing helper functions updated to handle both formats
