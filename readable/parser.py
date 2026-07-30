"""
parser.py - HTML Parser

Extracts merchant details from site HTML source code.
"""


def extract_js_variable(html_text, variable_name):
    """
    Extract a JavaScript variable value from HTML source.

    Looks for pattern: var VARNAME = "value";
    or: var VARNAME = 'value';
    or: var VARNAME = value;

    Args:
        html_text: Raw HTML containing JavaScript
        variable_name: Name of the JS variable to extract

    Returns:
        str: The variable's value (with quotes stripped)

    Raises:
        ValueError: If variable not found in HTML

    Example:
        >>> html = '<script>var MERCHANTID = "12345";</script>'
        >>> extract_js_variable(html, 'MERCHANTID')
        '12345'
    """
    try:
        # Split on 'var VARNAME = ' and take the part after
        after_var = html_text.split(f'var {variable_name} = ')[1]
        # Take everything before the semicolon
        value = after_var.split(';')[0]
        # Remove quotes and whitespace
        return value.strip('" \'')
    except IndexError:
        raise ValueError(f"Missing {variable_name}")


def get_merchant_details(html_text):
    """
    Extract MERCHANTID and MERCHANTNAME from site HTML.

    These values are embedded in JavaScript variables in the page source
    and are required for API authentication.

    Args:
        html_text: Raw HTML from the site's homepage

    Returns:
        tuple: (merchant_id, merchant_name)

    Raises:
        ValueError: If either value cannot be found

    Example:
        >>> html = '''
        ... <script>
        ... var MERCHANTID = "12345";
        ... var MERCHANTNAME = "Example Casino";
        ... </script>
        ... '''
        >>> get_merchant_details(html)
        ('12345', 'Example Casino')
    """
    merchant_id = extract_js_variable(html_text, 'MERCHANTID')
    merchant_name = extract_js_variable(html_text, 'MERCHANTNAME')
    return (merchant_id, merchant_name)


# Alias for backward compatibility
e = extract_js_variable
