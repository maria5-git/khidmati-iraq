# API Changes Report (تقرير التغييرات على واجهات API)

المطور: ماريا هيثم
التاريخ: 2026-09-06

 1. نقاط النهاية المعدلة (Modified Endpoints)

 1.1 إضافة الفلترة والبحث إلى قائمة البلاغات للمدير (`GET /api/v1/admin/reports`)

التغيير: تم دعم معاملات الاستعلام التالية (Query Parameters):
- `status`: فلترة حسب الحالة (`submitted`, `under_review`, `assigned`, `in_progress`, `resolved`, `rejected`, `cancelled`).
- `priority`: فلترة حسب الأولوية (`low`, `medium`, `high`, `urgent`).
- `category_id`: فلترة حسب رقم التصنيف.
- `governorate_id`: فلترة حسب رقم المحافظة.
- `assigned_employee_id`: فلترة حسب رقم الموظف المعين.
- `search`: بحث نصي في `reference_number`، `title`، و `description` (غير حساس لحالة الأحرف).
- `page`: رقم الصفحة (الافتراضي 1).
- `page_size`: عدد العناصر في الصفحة (الافتراضي 20، الحد الأقصى 100).

الاستجابة: أصبحت تعيد هيكل `PaginatedResponse` يحتوي على `page`, `page_size`, `total`, `total_pages`, `items`.

 1.2 عرض سجل التحديثات (`GET /api/v1/reports/{id}/history`)

التغيير: أصبح متاحاً للموظفين والمديرين بالإضافة إلى المواطن صاحب البلاغ.
- المواطن: يرى تاريخ بلاغاته فقط.
- الموظف: يرى تاريخ البلاغات في محافظته.
- المدير: يرى تاريخ أي بلاغ (صلاحية مطلقة).

 2. نقاط النهاية المضافة (New Endpoints)

 2.1 لوحة تحكم المدير (`GET /api/v1/admin/dashboard`)
- الصلاحية: المدير فقط.
- الوظيفة: عرض إحصائيات النظام:
  - `total_reports`: إجمالي البلاغات.
  - `open_reports`: البلاغات المفتوحة (غير `resolved`, `rejected`, `cancelled`).
  - `resolved_reports`: البلاغات المحلولة.
  - `by_status`: توزيع البلاغات حسب الحالة.
  - `by_priority`: توزيع البلاغات حسب الأولوية.
  - `by_category`: توزيع البلاغات حسب التصنيف (مع عرض الاسم العربي `name_ar`).

 2.2 إضافة ملاحظات داخلية للموظفين (`POST /api/v1/employee/reports/{id}/internal-notes`)
- الصلاحية: الموظفون والمديرون.
- الوظيفة: إضافة تعليق داخلي (`is_internal=True`) لا يراه المواطن.

 2.3 عرض جميع التعليقات للموظف (`GET /api/v1/employee/reports/{id}/comments`)
- الصلاحية: الموظفون والمديرون.
- الوظيفة: عرض التعليقات العامة والداخلية معاً (المواطن يرى العامة فقط).

 2.4 حل البلاغ (`POST /api/v1/employee/reports/{id}/resolve`)
- الصلاحية: الموظفون والمديرون.
- التحسينات:
  - أصبح حقل `resolution_summary` إجبارياً (لا يمكن أن يكون فارغاً أو يحتوي على مسافات فقط).
  - يتم تسجيل التغيير في سجل التاريخ (`status_history`) تلقائياً.
  - يتم حفظ وقت الحل (`resolved_at`) بتوقيت UTC.

 3. قواعد التحقق من الصلاحيات (Authorization Rules)

- المواطن (Citizen): لا يمكنه رؤية أو تعديل بلاغات المواطنين الآخرين (تم تطبيق `get_citizen_report_or_404`).
- الموظف (Employee): لا يمكنه الوصول إلى بلاغات خارج محافظته (تم تطبيق `get_report_for_employee`).
- المدير (Admin): لديه صلاحية مطلقة على جميع البلاغات والمستخدمين.

 4. سير عمل الحالات (Status Workflow)

تم تنفيذ قواعد الانتقال التالية (جدول `TRANSITIONS`):
- `submitted` ➡️ `under_review`, `rejected`, `cancelled`, `assigned`
- `under_review` ➡️ `assigned`, `rejected`
- `assigned` ➡️ `in_progress`, `under_review`
- `in_progress` ➡️ `resolved`, `assigned`
- `resolved`, `rejected`, `cancelled` ➡️ (حالات نهائية، لا يمكن الانتقال منها)

جميع الانتقالات غير المدرجة في الجدول مرفوضة وترجع خطأ `422`.

 5. أمثلة على استجابات الأخطاء (Error Responses)

-خطأ في الانتقال (422):
```json
{
  "detail": {
    "error": {
      "code": "INVALID_STATUS_TRANSITION",
      "message": "Cannot transition from 'submitted' to 'resolved'."
    }
  }
}

-ملخص الحل فارغ (400):
{
  "detail": {
    "error": {
      "code": "RESOLUTION_REQUIRED",
      "message": "Resolution summary is required and cannot be empty or whitespace only."
    }
  }
}

-منطقة لا تنتمي للمحافظة (400):

{
  "detail": {
    "error": {
      "code": "AREA_GOVERNORATE_MISMATCH",
      "message": "Area does not belong to the selected governorate."
    }
  }
}


*ملاحظة:تم الاستعانة بالذكاء الاصطناعي في كتابة هذا التقرير.