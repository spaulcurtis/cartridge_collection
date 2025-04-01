import re
from django.utils.safestring import mark_safe
from django.utils.html import linebreaks

def process_notes(note_text):
    """
    Process note text to separate public and confidential sections.
    Confidential sections are marked with double braces: {{confidential info}}
    
    Args:
        note_text (str): The original note text
        
    Returns:
        dict: A dictionary containing:
            - has_notes (bool): Whether there are any notes at all
            - public_notes (str): The public portion of the notes (HTML formatted)
            - confidential_notes (str): The confidential portion (HTML formatted)
            - has_confidential (bool): Whether there are any confidential notes
    """
    result = {
        'has_notes': bool(note_text),
        'public_notes': '',
        'confidential_notes': '',
        'has_confidential': False
    }
    
    if not note_text:
        return result
    
    # Find all confidential sections (text within double braces)
    confidential_pattern = r'{{(.*?)}}'
    confidential_matches = re.findall(confidential_pattern, note_text)
    
    # Extract confidential notes
    if confidential_matches:
        result['has_confidential'] = True
        confidential_text = '\n'.join(match.strip() for match in confidential_matches if match.strip())
        result['confidential_notes'] = mark_safe(linebreaks(confidential_text))
    
    # Extract public notes (everything not in double braces)
    public_text = re.sub(r'{{.*?}}', '', note_text).strip()
    if public_text:
        result['public_notes'] = mark_safe(linebreaks(public_text))
    
    return result

def process_object_notes(obj_list, note_field='note'):
    """
    Process notes for a list of objects.
    
    Args:
        obj_list (list): List of objects containing notes
        note_field (str): The field name containing the note text
        
    Returns:
        None (modifies objects in place)
    """
    for obj in obj_list:
        if hasattr(obj, note_field):
            note_text = getattr(obj, note_field)
            processed_notes = process_notes(note_text)
            
            # Add processed note attributes to the object
            for key, value in processed_notes.items():
                setattr(obj, f'{note_field}_{key}', value)
