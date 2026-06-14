def is_number(s):
    try:
        float(s)
    except ValueError:  # Failed
        return False
    else:  # Succeeded
        return True