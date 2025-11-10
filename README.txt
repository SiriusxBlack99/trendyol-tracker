Trendyol Category Tracker, FIXED

خطوات التشغيل على ويندوز:
1) افتح مجلد السكريبت.
2) شغّل install_venv_py312.bat لتثبيت المتطلبات والمتصفح.
3) شغّل setup_env.bat ثم افتح ملف .env وضع TELEGRAM_BOT_TOKEN و TELEGRAM_CHAT_ID.
4) عدل config.json برابط الكتاجوري، و"alert_type" و"alert_value".
   الأنواع المدعومة:
   - absolute_below: تنبيه إذا السعر الحالي <= القيمة. مثال 20 ريال.
   - percent_drop_at_least: تنبيه إذا نسبة الخصم >= القيمة. مثال 70.
   - absolute_saving_at_least: تنبيه إذا التوفير الحقيقي >= القيمة بالريال.
   يمكنك ضبط exclude_keywords, min_rating, min_reviews.
5) شغّل run_once_category.bat لتجربة واحدة، أو run_loop_category.bat للتشغيل الدوري حسب check_interval_minutes.

ملاحظات:
- السكريبت يمر على الصفحات باستخدام معامل pi في رابط البحث، ويقف إذا الصفحة فارغة عندما stop_on_empty=true.
- يضغط موافقة الكوكيز تلقائيًا، ويحاول قراءة السعر الحالي والسابق ونسبة الخصم من عناصر الصفحة الشائعة.
- يرسل تنبيه تيليجرام يتضمن السبب والسعر والعنوان والرابط.
- العملة في الرسائل تعتمد على الحقل currency في config، القيمة الافتراضية SAR.
