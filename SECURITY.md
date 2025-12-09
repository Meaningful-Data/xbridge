# Security Policy

## Supported Versions

We actively support the following versions with security updates:

| Version | Supported          | Status |
| ------- | ------------------ | ------ |
| 1.5.x   | :white_check_mark: | Current release (Release Candidate) |
| 1.4.x   | :white_check_mark: | Stable |
| 1.3.x   | :white_check_mark: | Stable |
| 1.2.x   | :white_check_mark: | Maintenance only |
| 1.1.x   | :white_check_mark: | Maintenance only |
| < 1.1   | :x:                | Not supported |

**Note**: We strongly recommend using the latest stable version (1.4.x) or the latest release candidate (1.5.x) for the best security and features.

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please help us by reporting it responsibly.

### How to Report

You can report a vulnerability through one of the following channels:

1. **GitHub Security Advisory** (Preferred):
   - Go to https://github.com/Meaningful-Data/xbridge/security/advisories/new
   - This allows us to collaborate privately on a fix before public disclosure

2. **Email**:
   - Send details to info@meaningfuldata.eu
   - Use subject line: "[SECURITY] XBridge Vulnerability Report"

3. **GitHub Issue** (For non-sensitive issues only):
   - Create an issue at https://github.com/Meaningful-Data/xbridge/issues
   - Only use this for low-severity issues that don't pose immediate risk

### What to Include

When reporting a vulnerability, please include:

- **Description**: Clear description of the vulnerability
- **Impact**: What could an attacker do with this vulnerability?
- **Reproduction steps**: Detailed steps to reproduce the issue
- **Affected versions**: Which versions are affected?
- **Proof of concept**: If possible, provide a minimal example
- **Suggested fix**: If you have ideas for how to fix it (optional)

### Response Timeline

- **Initial response**: Within 48 hours
- **Status update**: Within 5 business days
- **Fix timeline**: Depends on severity
  - Critical: Within 7 days
  - High: Within 14 days
  - Medium: Within 30 days
  - Low: Next regular release

### What to Expect

1. **Acknowledgment**: We'll confirm receipt of your report
2. **Assessment**: We'll evaluate the severity and impact
3. **Development**: We'll work on a fix (may involve you for clarification)
4. **Testing**: We'll test the fix thoroughly
5. **Disclosure**: We'll coordinate public disclosure timing with you
6. **Credit**: We'll credit you in the security advisory (unless you prefer to remain anonymous)

## Security Best Practices for Users

When using XBridge, we recommend:

### Input Validation
- **Validate input files**: Ensure XBRL-XML files come from trusted sources
- **Sanitize file paths**: Use absolute paths and validate they're within expected directories
- **Size limits**: Be cautious with very large files that could cause resource exhaustion

### Dependency Management
- **Keep updated**: Regularly update XBridge and its dependencies
- **Monitor advisories**: Watch for security advisories in dependencies (pandas, lxml, numpy)
- **Audit dependencies**: Use tools like `pip-audit` to check for known vulnerabilities

### File Handling
- **Temporary files**: XBridge creates temporary files during processing; ensure adequate disk space
- **Output validation**: Verify output files before use in production systems
- **Taxonomy files**: Only use official EBA taxonomy files from trusted sources

### Environment Security
- **Isolated environments**: Run XBridge in isolated virtual environments
- **Principle of least privilege**: Run with minimal necessary permissions
- **Network isolation**: If processing sensitive data, consider network isolation

### Example Secure Usage

```python
from pathlib import Path
from xbridge.api import convert_instance

# Use absolute paths
input_path = Path("/trusted/data/instance.xbrl").resolve()
output_path = Path("/secure/output").resolve()

# Validate input exists and is in expected directory
if not input_path.exists() or not input_path.is_file():
    raise ValueError("Invalid input file")

# Validate output directory
if not output_path.exists() or not output_path.is_dir():
    raise ValueError("Invalid output directory")

# Perform conversion with validation enabled
try:
    convert_instance(
        input_path,
        output_path,
        validate_filing_indicators=True,
        strict_validation=True,
    )
except Exception as e:
    # Handle errors appropriately
    print(f"Conversion failed: {e}")
```

## Known Security Considerations

### XML Processing
- XBridge uses `lxml` for XML processing, which is generally secure against common XML attacks
- We disable DTD processing and external entity expansion by default
- Very large XML files may consume significant memory

### File System Operations
- Taxonomy loading extracts compressed files to the file system
- Ensure adequate permissions and disk space
- Be cautious with taxonomy files from untrusted sources

### Data Privacy
- XBridge processes financial regulatory data that may be sensitive
- Ensure appropriate access controls on input and output files
- Consider encryption for data at rest and in transit

## Security Updates

Security updates are distributed through:

- **PyPI**: `pip install --upgrade eba-xbridge`
- **GitHub Releases**: https://github.com/Meaningful-Data/xbridge/releases
- **Security Advisories**: https://github.com/Meaningful-Data/xbridge/security/advisories

Subscribe to repository notifications to receive security alerts.

## Contact

For security-related questions or concerns:

- **Email**: info@meaningfuldata.eu
- **Company**: MeaningfulData - https://www.meaningfuldata.eu/
- **GitHub**: https://github.com/Meaningful-Data/xbridge

## Acknowledgments

We appreciate the security research community's efforts in keeping open source software secure. Thank you to all those who responsibly disclose vulnerabilities.
