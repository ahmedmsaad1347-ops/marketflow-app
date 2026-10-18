"""Configure and test SMTP locally. Never paste mail credentials into chat or GitHub."""
import argparse
import getpass
import os
from pathlib import Path
import shutil
import smtplib
import socket
import ssl
import subprocess
import sys
import tempfile
import warnings
from email.message import EmailMessage

from dotenv import dotenv_values, set_key
from email_validator import validate_email

# Support both `python tools/setup_mail.py` and the downloadable zip application.
if (Path.cwd() / 'backend/mail_delivery.py').is_file():
    sys.path.insert(0, str(Path.cwd()))
from backend.mail_delivery import SMTPSettings, send_smtp


class SetupError(ValueError):
    pass


def prompt(label, default=''):
    value = input(f'{label}' + (f' [{default}]' if default else '') + ': ').strip()
    return value or default


def normalized_email(value):
    return validate_email(value.strip(), check_deliverability=False).normalized


def private_password(label):
    if not sys.stdin.isatty():
        raise SetupError('شغّل الأداة مباشرة داخل Termux؛ لن نقرأ كلمة مرور من إدخال مكشوف.')
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        return getpass.getpass(label)


def collect_settings(provider, existing):
    if provider == 'gmail':
        account = normalized_email(prompt('Gmail المرسِل', existing.get('SMTP_USERNAME') or ''))
        print('استخدم App Password من Google، وليس كلمة مرور حسابك العادية.')
        print('إنشاء App Password: https://myaccount.google.com/apppasswords')
        password = ''.join(private_password('App Password (لن يظهر أثناء الكتابة): ').split())
        if len(password) != 16 or not password.isascii() or not password.isalnum():
            raise SetupError('كلمة مرور تطبيق Google تكون 16 حرفًا/رمزًا. انسخها من صفحة App passwords.')
        return SMTPSettings('smtp.gmail.com', 465, f'MarketFlow <{account}>', account, password).validate(), account
    host = prompt('SMTP host', existing.get('SMTP_HOST') or '')
    port = int(prompt('TLS port: 465 or 587', existing.get('SMTP_PORT') or '587'))
    sender = prompt('Verified sender, e.g. MarketFlow <no-reply@your-domain.com>', existing.get('SMTP_FROM') or '')
    username = prompt('SMTP username', existing.get('SMTP_USERNAME') or '')
    password = private_password('SMTP password (hidden): ') if username else ''
    recipient = normalized_email(prompt('Test recipient email'))
    return SMTPSettings(host, port, sender, username, password).validate(), recipient


def check_config_path(path):
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise SetupError('ملف .env لازم يكون ملفًا عاديًا داخل المشروع، وليس رابطًا أو مجلدًا.')
    if not path.parent.is_dir():
        raise SetupError('مجلد الإعدادات غير موجود. افتح الأداة من داخل مشروع MarketFlow.')
    result = subprocess.run(['git', 'ls-files', '--error-unmatch', '--', path.name], cwd=path.parent,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    if result.returncode == 0:
        raise SetupError('ملف الإعدادات متتبع في Git. توقفنا حتى لا ترفع كلمة المرور للمستودع.')
    in_repo = subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], cwd=path.parent,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode == 0
    if in_repo and subprocess.run(['git', 'check-ignore', '--quiet', '--', path.name], cwd=path.parent,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode != 0:
        raise SetupError('ملف الإعدادات غير مستثنى من Git. استخدم ملف .env داخل المشروع.')


def save_settings(path, settings):
    check_config_path(path)
    fd, temporary = tempfile.mkstemp(prefix='.env.smtp-', suffix='.tmp', dir=path.parent)
    os.close(fd)
    temporary = Path(temporary)
    try:
        if path.exists():
            shutil.copyfile(path, temporary)
        os.chmod(temporary, 0o600)
        values = {'SMTP_HOST': settings.host, 'SMTP_PORT': str(settings.port),
                  'SMTP_FROM': settings.sender, 'SMTP_USERNAME': settings.username,
                  'SMTP_PASSWORD': settings.password, 'AUTH_MAIL_MODE': 'smtp'}
        for key, value in values.items():
            set_key(temporary, key, value, quote_mode='always')
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def send_test(settings, recipient):
    message = EmailMessage()
    message['From'] = settings.sender
    message['To'] = recipient
    message['Subject'] = 'MarketFlow email delivery test'
    message.set_content('MarketFlow sent this message using the SMTP settings you just entered.\n\n'
                        'This is a delivery test, not an account verification link. Restart the MarketFlow API, '
                        'then sign in again to request a fresh verification email.\n')
    send_smtp(message, settings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=['gmail', 'smtp'], default='gmail')
    parser.add_argument('--env-file', default='.env')
    args = parser.parse_args()
    path = Path(args.env_file).absolute()
    print('إعداد البريد الحقيقي لـ MarketFlow — البيانات تُدخل عندك فقط.')
    print('الأداة تختبر إرسال رسالة أولاً؛ لا تغيّر الإعدادات إذا فشل الاختبار.')
    try:
        if not (Path.cwd() / 'backend/main.py').is_file():
            raise SetupError('افتح مجلد المشروع أولاً: cd ~/marketflow-app')
        check_config_path(path)
        existing = dotenv_values(path) if path.exists() else {}
        settings, recipient = collect_settings(args.provider, existing)
        print('جاري اختبار اتصال TLS والمصادقة وإرسال رسالة الاختبار…')
        send_test(settings, recipient)
        save_settings(path, settings)
    except smtplib.SMTPAuthenticationError:
        print('رفض خادم البريد المصادقة. راجع عنوان Gmail وApp Password وتفعيل التحقق بخطوتين. لم نحفظ إعدادات جديدة.', file=sys.stderr)
        return 1
    except ssl.SSLError:
        print('فشل التحقق من اتصال TLS. راجع وقت الجهاز والشهادات والشبكة؛ لا تعطّل TLS. لم نحفظ إعدادات جديدة.', file=sys.stderr)
        return 1
    except (socket.timeout, ConnectionError, OSError):
        print('تعذر الاتصال أو حفظ الملف. راجع الإنترنت والوصول لمنفذ البريد ومسار المشروع. لم نفعّل البريد الجديد.', file=sys.stderr)
        return 1
    except smtplib.SMTPException:
        print('خادم البريد رفض الإرسال. راجع توثيق المرسِل وصلاحياته وحدود الخدمة. لم نحفظ إعدادات جديدة.', file=sys.stderr)
        return 1
    except SetupError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (ValueError, getpass.GetPassWarning):
        print('تعذر إكمال الإعداد. راجع عنوان البريد وبيانات SMTP، واستخدم App Password من 16 رمزًا لـGmail. لم نحفظ إعدادات جديدة.', file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print('\nتم إلغاء الإعداد دون حفظ بيانات جديدة.', file=sys.stderr)
        return 1
    print('خادم SMTP قبل رسالة الاختبار، وتم حفظ الإعدادات في .env بصلاحية خاصة.')
    print('تأكد من وصول MarketFlow email delivery test في Inbox أو Spam؛ قبول SMTP لا يضمن وصول Inbox.')
    overrides = [key for key in ('AUTH_MAIL_MODE', 'SMTP_HOST', 'SMTP_PORT', 'SMTP_FROM', 'SMTP_USERNAME', 'SMTP_PASSWORD') if key in os.environ]
    if overrides:
        print('تنبيه: في متغيرات بريد مصدّرة في جلسة Termux. ابدأ جلسة جديدة للباكإند حتى لا تتجاوز إعدادات .env.')
    print('أوقف الباكإند القديم بـCtrl+C ثم أعد تشغيله. حدّث صفحة Chrome وادخل من /login لطلب رابط تأكيد جديد.')
    print('الرابط يُفتح في نفس Chrome. احتفظ بكلمة مرور التطبيق في جهازك ولا ترسلها في الشات أو الصور.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
