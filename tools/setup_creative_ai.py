"""Configure Creative Studio privately on the user's device; never paste keys into chat."""
import os
import getpass
from pathlib import Path
import re
import shutil
import sys
import tempfile
from urllib.parse import quote

import httpx
from dotenv import dotenv_values, set_key

sys.path.insert(0,str(Path(__file__).resolve().parent))
from setup_mail import SetupError, check_config_path, private_password, prompt


def save_ai_settings(path,key,model):
    check_config_path(path)
    handle,temporary=tempfile.mkstemp(prefix='.env.ai-',suffix='.tmp',dir=path.parent)
    os.close(handle)
    temporary=Path(temporary)
    try:
        if path.exists():shutil.copyfile(path,temporary)
        os.chmod(temporary,0o600)
        for name,value in {'OPENAI_API_KEY':key,'OPENAI_MODEL':model}.items():
            set_key(temporary,name,value,quote_mode='always')
        os.replace(temporary,path)
        os.chmod(path,0o600)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    print('تفعيل وكيل كتابة المحتوى — المفتاح يُدخل هنا فقط ولا يظهر في الشاشة.')
    print('تحتاج مفتاح OpenAI API بصلاحية الاستخدام؛ اشتراك ChatGPT منفصل عن فوترة API.')
    print('الأداة تتحقق من الوصول للموديل دون توليد محتوى، وتحافظ على إعدادات البريد والمنصات.')
    path=Path.cwd()/'.env'
    try:
        if not (Path.cwd()/'backend/creative_studio.py').is_file():
            raise SetupError('افتح المشروع بعد تثبيت التحديث: cd ~/marketflow-app')
        check_config_path(path)
        existing=dotenv_values(path) if path.exists() else {}
        model=prompt('Model',existing.get('OPENAI_MODEL') or 'gpt-4.1-mini')
        if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}',model):
            raise SetupError('اسم الموديل غير صالح.')
        key=private_password('OpenAI API key (hidden): ').strip()
        if not key or any(char.isspace() for char in key):
            raise SetupError('المفتاح فارغ أو يحتوي على مسافات. لم نحفظ إعدادات جديدة.')
        response=httpx.get('https://api.openai.com/v1/models/'+quote(model,safe=''),
            headers={'Authorization':'Bearer '+key},timeout=20)
        response.raise_for_status()
        save_ai_settings(path,key,model)
    except SetupError as error:
        print(str(error),file=sys.stderr);return 1
    except httpx.HTTPError:
        print('تعذر التحقق من المفتاح أو الوصول للموديل. راجع الاتصال والصلاحيات؛ لم نحفظ إعدادات جديدة.',file=sys.stderr);return 1
    except (OSError,ValueError,getpass.GetPassWarning):
        print('تعذر إكمال الإعداد. لم نعرض المفتاح. راجع مسار المشروع وبيانات الموديل.',file=sys.stderr);return 1
    except (KeyboardInterrupt,EOFError):
        print('\nتم إلغاء الإعداد.',file=sys.stderr);return 1
    print('تم التحقق من الوصول للموديل وحفظ المفتاح في .env بصلاحية 0600.')
    print('ده يثبت الوصول للموديل فقط. أول توليد محتوى سيختبر صلاحية التوليد والفوترة.')
    if any(name in os.environ for name in ('OPENAI_API_KEY','OPENAI_MODEL')):
        print('في متغير AI مصدّر بالجِلسة. افتح جلسة جديدة للباكإند حتى لا يتجاوز إعدادات .env.')
    print('أوقف الباكإند القديم بـCtrl+C وأعد تشغيله. افتح Creative Studio؛ ستظهر AI writing agent connected.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
