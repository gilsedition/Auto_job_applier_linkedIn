'''
Author:     Sai Vignesh Golla
LinkedIn:   https://www.linkedin.com/in/saivigneshgolla/

Copyright (C) 2024 Sai Vignesh Golla

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/GodsScion/Auto_job_applier_linkedIn

Support me: https://github.com/sponsors/GodsScion

version:    26.01.20.5.08
'''

from modules.helpers import get_default_temp_profile, make_directories
from config.settings import run_in_background, stealth_mode, disable_extensions, safe_mode, file_name, failed_file_name, logs_folder_path, generated_resume_path, chrome_profile_name, bot_profile_dir, auto_close_conflicting_chrome
from config.questions import default_resume_path
import os
import time
import subprocess
if stealth_mode:
    import undetected_chromedriver as uc
else: 
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    # from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from modules.helpers import find_default_profile_directory, critical_error_log, print_lg, find_profile_folder_by_name
from selenium.common.exceptions import SessionNotCreatedException

def get_isolated_temp_profile() -> str:
    base_dir = get_default_temp_profile()
    return os.path.join(base_dir, f"session-{int(time.time())}-{os.getpid()}")


def close_conflicting_chrome_sessions(profile_dir: str) -> None:
    '''On Windows, close only Chrome/ChromeDriver processes that are using the given profile dir.'''
    if not profile_dir or os.name != 'nt':
        return

    normalized = os.path.normpath(profile_dir).replace("'", "''")
    ps_script = (
        "$profileDir = '" + normalized + "';"
        "$targets = Get-CimInstance Win32_Process | Where-Object {"
        "($_.Name -match '^(chrome|chromedriver)\\.exe$') -and $_.CommandLine -and "
        "($_.CommandLine.ToLower().Contains('--user-data-dir=' + $profileDir.ToLower()) -or "
        " $_.CommandLine.ToLower().Contains($profileDir.ToLower()))"
        "};"
        "$killed = @();"
        "foreach ($p in $targets) {"
        "  try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop; $killed += $p.ProcessId } catch {}"
        "};"
        "if ($killed.Count -gt 0) { Write-Output ('KILLED_PIDS:' + ($killed -join ',')) }"
    )

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        output = (result.stdout or "").strip()
        if output:
            print_lg(f"Closed conflicting Chrome sessions for bot profile. {output}")
        else:
            print_lg("No conflicting Chrome sessions found for bot profile.")
    except Exception as e:
        print_lg("Failed to auto-close conflicting Chrome sessions.", e)


def createChromeSession(isRetry: bool = False, retry_profile_dir: str | None = None):
    make_directories([file_name,failed_file_name,logs_folder_path+"/screenshots",default_resume_path,generated_resume_path+"/temp"])
    # Set up WebDriver with Chrome Profile
    options = uc.ChromeOptions() if stealth_mode else Options()
    if not stealth_mode:
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-features=ChromeWhatsNewUI")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
    if run_in_background:   options.add_argument("--headless")
    if disable_extensions:  options.add_argument("--disable-extensions")

    print_lg("IF YOU HAVE MORE THAN 10 TABS OPENED, PLEASE CLOSE OR BOOKMARK THEM! Or it's highly likely that application will just open browser and not do anything!")
    if isRetry:
        print_lg("Will login with a guest profile, browsing history will not be saved in the browser!")
        retry_profile = retry_profile_dir or get_default_temp_profile()
        make_directories([retry_profile])
        print_lg(f'Using isolated retry profile directory: "{retry_profile}"')
        options.add_argument(f"--user-data-dir={retry_profile}")
    elif bot_profile_dir:
        print_lg(f'Using dedicated bot profile directory: "{bot_profile_dir}"')
        options.add_argument(f"--user-data-dir={bot_profile_dir}")
    elif not safe_mode:
        profile_dir = find_default_profile_directory()
        if profile_dir:
            if chrome_profile_name:
                profile_folder = find_profile_folder_by_name(profile_dir, chrome_profile_name)
                if profile_folder:
                    print_lg(f'Using Chrome profile: "{chrome_profile_name}" ({profile_folder})')
                    options.add_argument(f"--user-data-dir={profile_dir}")
                    options.add_argument(f"--profile-directory={profile_folder}")
                else:
                    print_lg(f'Chrome profile "{chrome_profile_name}" not found, falling back to default profile.')
                    options.add_argument(f"--user-data-dir={profile_dir}")
            else:
                options.add_argument(f"--user-data-dir={profile_dir}")
        else:
            print_lg("Logging in with a guest profile, Web history will not be saved!")
            options.add_argument(f"--user-data-dir={get_default_temp_profile()}")
    else:
        print_lg("Logging in with a guest profile, Web history will not be saved!")
        options.add_argument(f"--user-data-dir={get_default_temp_profile()}")
    if stealth_mode:
        # try: 
        #     driver = uc.Chrome(driver_executable_path="C:\\Program Files\\Google\\Chrome\\chromedriver-win64\\chromedriver.exe", options=options)
        # except (FileNotFoundError, PermissionError) as e: 
        #     print_lg("(Undetected Mode) Got '{}' when using pre-installed ChromeDriver.".format(type(e).__name__)) 
            print_lg("Downloading Chrome Driver... This may take some time. Undetected mode requires download every run!")
            driver = uc.Chrome(options=options)
    else: driver = webdriver.Chrome(options=options) #, service=Service(executable_path="C:\\Program Files\\Google\\Chrome\\chromedriver-win64\\chromedriver.exe"))
    driver.maximize_window()
    wait = WebDriverWait(driver, 5)
    actions = ActionChains(driver)
    return options, driver, actions, wait

try:
    options, driver, actions, wait = None, None, None, None
    options, driver, actions, wait = createChromeSession()
except SessionNotCreatedException as e:
    critical_error_log("Failed to create Chrome Session, retrying with guest profile", e)
    session_started = False

    if auto_close_conflicting_chrome and bot_profile_dir:
        close_conflicting_chrome_sessions(bot_profile_dir)
        try:
            print_lg("Retrying Chrome session with dedicated bot profile after closing conflicts...")
            options, driver, actions, wait = createChromeSession()
            session_started = True
        except SessionNotCreatedException as post_close_error:
            critical_error_log("Retry with dedicated profile after auto-close failed", post_close_error)

    if not session_started:
        try:
            options, driver, actions, wait = createChromeSession(True, get_isolated_temp_profile())
        except SessionNotCreatedException as retry_error:
            critical_error_log("Retry with isolated guest profile failed", retry_error)
            raise
except Exception as e:
    msg = 'Seems like Google Chrome is out dated. Update browser and try again! \n\n\nIf issue persists, try Safe Mode. Set, safe_mode = True in config.py \n\nPlease check GitHub discussions/support for solutions https://github.com/GodsScion/Auto_job_applier_linkedIn \n                                   OR \nReach out in discord ( https://discord.gg/fFp7uUzWCY )'
    if isinstance(e,TimeoutError): msg = "Couldn't download Chrome-driver. Set stealth_mode = False in config!"
    print_lg(msg)
    critical_error_log("In Opening Chrome", e)
    from pyautogui import alert
    alert(msg, "Error in opening chrome")
    try: driver.quit()
    except NameError: exit()
    
