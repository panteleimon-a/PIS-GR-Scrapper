## Brief overview
- Guidelines for developing a Python Selenium automation script to log into the Greek Medical Association portal, navigate to a target page, and save its HTML output in a robust, maintainable way.

## Communication style
- Provide concise, technical explanations in markdown format.  
- Label code blocks with the correct language (e.g., “Python”).  
- After each code snippet, include a progress statement (e.g., “Progress: Step 1 complete.”).

## Development workflow
- Break the task into incremental steps and implement each as its own markdown section.  
- Confirm completion of each step before moving on.  
- Organize source files into a clear structure:  
  - `bot.py` for main logic  
  - `credentials.json` for secrets  
  - `application_view.html` as output  
  - `test_bot.py` for automated tests  

## Credential management
- Always read credentials from `credentials.json`; never hardcode sensitive data.  
- Expect JSON format:  
  ```json
  {
    "username": "YOUR_USERNAME_HERE",
    "password": "YOUR_PASSWORD_HERE"
  }
  ```  

## Browser configuration
- Use ChromeOptions configured for headless operation (no visible window).  
- Ensure `chromedriver` is accessible on the system PATH.  
- Employ `WebDriverWait` with `expected_conditions` to wait for elements before interacting.

## Error handling & cleanup
- Wrap Selenium interactions in `try/except` blocks catching `TimeoutException` and `NoSuchElementException`.  
- Print clear, user-friendly error messages on failure.  
- Use a `finally` block to call `driver.quit()` and guarantee browser closure.

## Scheduling
- For one-shot execution, use the `schedule` library with `schedule.every().tuesday.at("14:00").do(...)`.  
- After the task runs once, cancel the job to prevent further scheduling.

## Testing strategy
- Create `test_bot.py` using pytest to invoke the main function.  
- Use a test credentials file or mock to simulate login.  
- Assert that `application_view.html` is generated and contains key HTML elements (e.g., page title, known IDs).

## Documentation retrieval
- When needing package documentation (e.g., Selenium, schedule), use the Context7 MCP server to fetch up-to-date docs.  
- Call `resolve-library-id` then `get-library-docs` for precise information on library functions and usage.
