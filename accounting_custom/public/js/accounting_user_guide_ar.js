window.accounting_custom = window.accounting_custom || {};

accounting_custom.get_arabic_accounting_guide = function (image_root) {
	return `
		<div class="accounting-guide" dir="rtl" lang="ar">
			<section class="ag-hero">
				<div class="ag-hero-copy">
					<div class="ag-eyebrow">الدليل التشغيلي للمحاسبة</div>
					<h1>إدارة الدورة المالية بثقة، من استلام المستند إلى المراجعة والاعتماد</h1>
					<p>دليل عملي للمحصّلين والمحاسبين ومسؤولي الشؤون المالية وأمناء الصناديق والمديرين وأصحاب صلاحية الاعتماد.</p>
					<div class="ag-actions"><button class="btn btn-primary" data-route="workspace">فتح مساحة عمل المحاسبة</button><button class="btn btn-default" data-scroll="quick-start">البدء بقائمة المراجعة اليومية</button></div>
					<div class="ag-role-shortcuts"><span>عرض الدليل بحسب الدور:</span><button data-role-shortcut="accountant">المحاسب</button><button data-role-shortcut="manager">المدير وصاحب الاعتماد</button></div>
				</div>
				<div class="ag-hero-stat"><strong>12</strong><span>تقريراً رقابياً وإدارياً</span><strong>15</strong><span>وحدة تدريبية</span></div>
			</section>

			<section class="ag-learning-path">
				<div><b>1</b><span><strong>مبتدئ</strong>التنقل والمصطلحات</span></div><i>←</i><div><b>2</b><span><strong>تأسيس</strong>الشركات والحسابات والأطراف</span></div><i>←</i><div><b>3</b><span><strong>تشغيل</strong>المقبوضات والمدفوعات والرواتب</span></div><i>←</i><div><b>4</b><span><strong>مراجعة</strong>الموافقات والضوابط</span></div><i>←</i><div><b>5</b><span><strong>احتراف</strong>التقارير والإقفال الدوري</span></div>
			</section>

			<nav class="ag-tabs" aria-label="فئة مستخدم الدليل"><button class="active" data-audience="all">الدليل الكامل</button><button data-audience="accountant">المحاسب</button><button data-audience="manager">المدير وصاحب الاعتماد</button><label class="ag-search"><span>⌕</span><input type="search" placeholder="البحث في الدليل..." aria-label="البحث في الدليل"></label></nav>
			<nav class="ag-topic-nav" aria-label="موضوعات الدليل">
				<button class="active" data-topic="all">جميع الموضوعات</button><button data-topic="quick-start">المراجعة اليومية</button><button data-topic="navigation">التنقل</button><button data-topic="setup">التهيئة والبيانات الأساسية</button><button data-topic="donations">التبرعات</button><button data-topic="payments">المدفوعات المباشرة</button><button data-topic="memos">مذكرات الدفع</button><button data-topic="payroll">الرواتب</button><button data-topic="controls">الضوابط المحاسبية</button><button data-topic="core">أدوات ERPNext</button><button data-topic="examples">أمثلة تطبيقية</button><button data-topic="approvals">الصلاحيات والموافقات</button><button data-topic="reports">التقارير</button><button data-topic="closing">الإقفال الدوري</button><button data-topic="troubleshooting">معالجة الأخطاء</button><button data-topic="glossary">المصطلحات</button>
			</nav>

			<section class="ag-section" id="quick-start" data-topic="quick-start" data-audience="all accountant manager" data-search="يومي مراجعة محاسبة">
				<div class="ag-section-heading"><span>01</span><div><h2>نقطة الانطلاق اليومية</h2><p>اتبع هذا التسلسل قبل إدخال أي معاملة أو اعتمادها.</p></div></div>
				<div class="ag-checklist"><div><b>1</b><span><strong>تأكيد سياق المعاملة</strong>راجع الشركة والفرع وتاريخ الترحيل والعملة ومركز التكلفة.</span></div><div><b>2</b><span><strong>اختيار المسار الصحيح</strong>استخدم سند التبرع للمقبوضات، وسند الصرف المحاسبي للدفع المباشر، ومذكرة الدفع للطلبات الخاضعة لمسار موافقات.</span></div><div><b>3</b><span><strong>استكمال المستندات المؤيدة</strong>أدخل الطرف والمشروع والمرجع وأرفق الفاتورة أو الإثبات قبل طلب الموافقة.</span></div><div><b>4</b><span><strong>المراجعة قبل الاعتماد</strong>تحقق من الحسابات والعملات والإجماليات وحالة الموافقة والتوزيع على مراكز التكلفة.</span></div></div>
			</section>

			<section class="ag-section" data-topic="navigation" data-audience="all accountant manager" data-search="مساحة العمل تنقل تقارير">
				<div class="ag-section-heading"><span>02</span><div><h2>الوصول إلى أدوات المحاسبة</h2><p>افتح «المحاسبة» من الشريط الجانبي، ثم انتقل إلى بطاقات العمليات والتقارير المحاسبية.</p></div></div>
				<figure class="ag-shot"><img src="${image_root}/accounting-workspace-overview.png" alt="شرح مساحة عمل المحاسبة باللغة العربية"><figcaption>تجمع مساحة عمل المحاسبة السجلات الأساسية ودورات العمل والتقارير في أقسام واضحة بحسب المهمة.</figcaption></figure>
			</section>

			<section class="ag-section" data-topic="setup" data-audience="all accountant manager" data-search="تهيئة شركة فرع حساب عملة متبرع محصل مركز تكلفة">
				<div class="ag-section-heading"><span>03</span><div><h2>التهيئة والبيانات الأساسية</h2><p>تعتمد سلامة القيود والتقارير على اكتمال إعدادات الشركة والحسابات والأطراف قبل بدء العمل.</p></div></div>
				<div class="ag-table-wrap"><table><thead><tr><th>عنصر التهيئة</th><th>المسار</th><th>النتيجة المطلوبة</th></tr></thead><tbody><tr><td>الشركة والفرع</td><td>الشركة / الفرع</td><td>عملة افتراضية وفرع تشغيلي صحيح.</td></tr><tr><td>الصندوق والبنك</td><td>طريقة الدفع ← الحسابات</td><td>حساب صالح للشركة لكل طريقة دفع وعملة.</td></tr><tr><td>أسعار الصرف</td><td><button data-doctype="Company Exchange Rate">سعر صرف الشركة</button></td><td>سعر نافذ بتاريخ الترحيل لتحويل عملة المعاملة إلى عملة الشركة.</td></tr><tr><td>حساب المتبرع</td><td>المتبرع ← الحسابات</td><td>ربط المتبرع بالشركة وحساب إيراد التبرعات الصحيح.</td></tr><tr><td>عهدة المحصّل</td><td><button data-doctype="Collector Profile">ملف المحصّل</button></td><td>مستخدم فعّال وحساب عهدة مستقل لكل عملة.</td></tr><tr><td>أطراف الدفع</td><td>موظف / مورّد / <button data-doctype="Institution">مؤسسة</button></td><td>ربط الطرف بالشركة والحساب الملائم عند الحاجة.</td></tr><tr><td>الأبعاد التحليلية</td><td>مركز التكلفة / المشروع</td><td>سجلات تفصيلية غير تجميعية تابعة للشركة.</td></tr></tbody></table></div>
				<div class="ag-note"><strong>مسؤولية التهيئة:</strong> يدير مسؤول النظام الصلاحيات والبيانات الأساسية، وتتولى الشؤون المالية دليل الحسابات وأسعار الصرف ومراكز التكلفة وضوابط الترحيل، بينما يراجع أمين الصندوق جاهزية حسابات النقد والبنوك.</div>
			</section>

			<section class="ag-section" data-topic="donations" data-audience="all accountant" data-search="تبرع متبرع محصل عهدة قبض تسليم">
				<div class="ag-section-heading"><span>04</span><div><h2>دورة التبرع وعهدة المحصّل</h2><p>أثبت المقبوض فوراً، وأبقِ المبلغ في عهدة المحصّل إلى حين تسليمه إلى الصندوق أو البنك.</p></div></div>
				<figure class="ag-shot ag-diagram"><img src="${image_root}/donation-custody-workflow.png" alt="دورة التبرع وعهدة المحصل"><figcaption>المسار الكامل من تحصيل التبرع ومراجعته إلى تسليم العهدة وإثباتها في الخزينة.</figcaption></figure>
				<div class="ag-flow"><div><em>1</em><strong>ملف المحصّل</strong><small>راجع حساب المتبرع الافتراضي وحساب العهدة لكل عملة.</small><button data-doctype="Collector Profile">فتح</button></div><i>←</i><div><em>2</em><strong>سند التبرع</strong><small>حدد المتبرع والمشروع والعملة والمبلغ والحساب.</small><button data-doctype="Donation Entry">فتح</button></div><i>←</i><div><em>3</em><strong>المراجعة المالية</strong><small>تراجع الشؤون المالية صحة المستند والتوجيه المحاسبي.</small></div><i>←</i><div><em>4</em><strong>تسليم المحصّل</strong><small>يستلم أمين الصندوق المبلغ وينقله من العهدة إلى الصندوق أو البنك.</small><button data-doctype="Collector Handover">فتح</button></div></div>
				<div class="ag-detail-grid"><div><h3>قبل الاعتماد</h3><ol><li>حدد الشركة والمتبرع وحسابه والمشروع عند الحاجة.</li><li>أضف سطراً مستقلاً لكل عملة وطريقة دفع.</li><li>حدد حساب الإيراد ومركز التكلفة.</li><li>أرفق الإثبات واطلب المراجعة المالية.</li></ol></div><div><h3>بعد الاعتماد</h3><ol><li>اعتمد السند لإنشاء القيود المحاسبية.</li><li>سلّم نسخة سند القبض إلى المتبرع.</li><li>تابع الرصيد في عهدة المحصّل.</li><li>أنشئ مستند تسليم المحصّل عند استلام الخزينة للمبلغ.</li></ol></div></div>
			</section>

			<section class="ag-section" data-topic="payments" data-audience="all accountant" data-search="صرف دفع مستفيد موظف مورد مؤسسة">
				<div class="ag-section-heading"><span>05</span><div><h2>سند الصرف المحاسبي</h2><p>يستخدم لإثبات المدفوعات المباشرة بعد تحديد مصدر الدفع والتوجيه المحاسبي ومركز التكلفة.</p></div></div>
				<figure class="ag-shot"><img src="${image_root}/accounting-payment-entry.png" alt="شرح سند الصرف المحاسبي"><figcaption>يُختار نوع الطرف بحسب طبيعة المستفيد، مع التحقق من الشركة والحساب والعملة قبل الاعتماد.</figcaption></figure>
				<div class="ag-rule-grid"><div><strong>مستفيد</strong><span>متاح لجميع الشركات.</span></div><div><strong>موظف</strong><span>يُرشح بحسب شركة الموظف.</span></div><div><strong>مورّد</strong><span>يُرشح من جدول حسابات المورّد.</span></div><div><strong>مؤسسة</strong><span>تُرشح بحسب الشركة المرتبطة.</span></div></div>
				<div class="ag-detail-grid"><div><h3>إدخال سند الصرف</h3><ol><li>حدد الشركة وتاريخ الترحيل والفرع.</li><li>أضف سطراً لكل حساب ومركز تكلفة.</li><li>حدد طريقة الدفع والحساب والعملة والمبلغ.</li><li>حدد نوع الطرف والمستفيد عندما يتطلب الحساب ذلك.</li></ol></div><div><h3>المراجعة والترحيل</h3><ol><li>راجع إجماليات العملات وسعر الصرف.</li><li>أرسل السند للمراجعة المالية.</li><li>تعتمد الشؤون المالية السند أو تعيده مع ملاحظات أو ترفضه.</li><li>اعتمد المستند بعد الموافقة؛ وعند الإلغاء ينشئ النظام قيوداً عكسية.</li></ol></div></div>
			</section>

			<section class="ag-section" data-topic="memos" data-audience="all accountant manager" data-search="مذكرة دفع عهدة سلفة راتب موافقة">
				<div class="ag-section-heading"><span>06</span><div><h2>مذكرة الدفع والعهد</h2><p>حدد نوع المذكرة بدقة، لأن مسار الاعتماد والمعالجة المحاسبية يتغيران بحسب الغرض.</p></div></div>
				<figure class="ag-shot ag-diagram"><img src="${image_root}/payment-memo-workflow.png" alt="مسارات اعتماد مذكرة الدفع"><figcaption>توضح الصورة مسار كل نوع من الطلب إلى المراجعة المالية واعتماد الرئيس والتنفيذ لدى أمين الصندوق.</figcaption></figure>
				<div class="ag-cards"><article><span class="ag-tag">دفع</span><h3>دفعة عادية</h3><p>مقدم الطلب ← المدير المسؤول ← المالية ← الرئيس ← أمين الصندوق.</p></article><article><span class="ag-tag">عهدة</span><h3>طلب عهدة</h3><p>يستخدم عندما سيسوّي المستفيد المصروف لاحقاً بمستندات مؤيدة.</p></article><article><span class="ag-tag">تسوية</span><h3>إقفال عهدة</h3><p>يرتبط بالعهدة الأصلية ولا يجوز أن يتجاوز رصيدها القائم.</p></article><article><span class="ag-tag">راتب</span><h3>سلفة راتب</h3><p>الموظف ← منسق الموارد البشرية ← المدير ← المالية ← الرئيس ← أمين الصندوق.</p></article></div>
				<div class="ag-note"><strong>ضابط مالي:</strong> لا تنتقل المذكرة إلى المرحلة التالية قبل اكتمال الحسابات ومراكز التكلفة والمشاريع والمرفقات وتحديد حساب الدفع أو العهدة.</div>
			</section>

			<section class="ag-section" data-topic="payroll" data-audience="all accountant" data-search="رواتب توزيع تكلفة حسميات مراجعة">
				<div class="ag-section-heading"><span>07</span><div><h2>إعداد الرواتب ومراجعتها</h2><p>تتولى الشؤون المالية توزيع التكلفة، وتدخل الموارد البشرية الحسميات، ثم يراجع أصحاب الصلاحية سجل الرواتب.</p></div></div>
				<figure class="ag-shot ag-diagram"><img src="${image_root}/payroll-cycle.png" alt="دورة الرواتب الشهرية"><figcaption>الدورة الشهرية من تثبيت الاستحقاق وتوزيع التكلفة إلى المراجعة النهائية والدفع.</figcaption></figure>
				<div class="ag-table-wrap"><table><thead><tr><th>المهمة</th><th>المسؤول</th><th>المستند</th><th>الضابط</th></tr></thead><tbody><tr><td>توزيع تكلفة الراتب</td><td>الشؤون المالية</td><td><button data-doctype="Payroll Cost Center Allocation">توزيع مراكز تكلفة الرواتب</button></td><td>يجب أن يبلغ مجموع النسب 100%.</td></tr><tr><td>الحسميات الشهرية</td><td>الموارد البشرية / المالية</td><td><button data-doctype="Employee Monthly Adjustment">تسوية الموظف الشهرية</button></td><td>ينشئ النظام مستندات راتب إضافية معتمدة للحسم.</td></tr><tr><td>مراجعة سجل الرواتب</td><td>المدير التنفيذي / الرئيس</td><td><button data-doctype="Payroll Review">مراجعة الرواتب</button></td><td>توثيق الملاحظات ثم الإعادة أو الاعتماد.</td></tr></tbody></table></div>
			</section>

			<section class="ag-section" data-topic="controls" data-audience="all accountant manager" data-search="مدين دائن قيد رقابة مطابقة">
				<div class="ag-section-heading"><span>08</span><div><h2>الأثر المحاسبي والضوابط</h2><p>يجب فهم القيد الناتج عن كل معاملة قبل اعتمادها.</p></div></div>
				<div class="ag-table-wrap"><table><thead><tr><th>المعاملة</th><th>الطرف المدين</th><th>الطرف الدائن</th><th>الضابط الأساسي</th></tr></thead><tbody><tr><td>تحصيل تبرع بواسطة محصّل</td><td>حساب عهدة المحصّل</td><td>حساب إيراد التبرعات</td><td>وجود حساب عهدة مطابق للعملة.</td></tr><tr><td>تسليم المحصّل</td><td>الصندوق أو البنك</td><td>عهدة المحصّل</td><td>ألا يتجاوز التسليم الرصيد غير المسلّم.</td></tr><tr><td>سند صرف محاسبي</td><td>حساب المصروف أو التخصيص</td><td>حساب طريقة الدفع</td><td>الموافقة المالية وصحة الشركة والحسابات.</td></tr><tr><td>إلغاء مستند معتمد</td><td colspan="2">قيد عكسي يحافظ على أثر التدقيق</td><td>لا تُحذف القيود المالية المعتمدة.</td></tr></tbody></table></div>
				<div class="ag-detail-grid"><div><h3>ضوابط يومية</h3><ul><li>راجع تقرير الموافقات المحاسبية المعلقة.</li><li>طابق حركة الخزينة مع المستندات النقدية.</li><li>تابع العهد القديمة وتسليمات المحصّلين.</li><li>تحقق من الفرع ومركز التكلفة في كل قيد.</li></ul></div><div><h3>ضوابط نهاية الفترة</h3><ul><li>طابق حسابات الصندوق والبنوك.</li><li>راجع العهد المفتوحة والمستندات المعادة.</li><li>قارن التقارير الأسبوعية والشهرية.</li><li>لا تقفل الفترة قبل معالجة الفروقات وتوثيق المراجعة.</li></ul></div></div>
			</section>

			<section class="ag-section" data-topic="core" data-audience="all accountant manager" data-search="دليل الحسابات قيد يومية فاتورة ميزان مراجعة">
				<div class="ag-section-heading"><span>09</span><div><h2>أدوات المحاسبة الأساسية في ERPNext</h2><p>تكمل التخصيصات الدورة المحاسبية القياسية ولا تستبدل دفاتر الأستاذ والضوابط الأصلية.</p></div></div>
				<div class="ag-table-wrap"><table><thead><tr><th>الأداة</th><th>الاستخدام الصحيح</th><th>استخدام غير صحيح</th></tr></thead><tbody><tr><td><button data-doctype="Account">دليل الحسابات</button></td><td>تنظيم الأصول والالتزامات وحقوق الملكية والإيرادات والمصروفات.</td><td>إنشاء حساب جديد لكل معاملة.</td></tr><tr><td><button data-doctype="Journal Entry">قيد اليومية</button></td><td>قيود الاستحقاق والتصحيح والتحويل والأرصدة الافتتاحية وفروق الصرف.</td><td>تجاوز مسار سند التبرع أو مذكرة الدفع.</td></tr><tr><td><button data-doctype="Payment Entry">سند الدفع القياسي</button></td><td>تسوية ذمم العملاء والمورّدين.</td><td>إدارة عهد المحصّلين أو الموافقات الداخلية.</td></tr><tr><td>المطابقة البنكية</td><td>مطابقة كشف البنك مع القيود المرحلة.</td><td>تغيير تاريخ الترحيل لمجرد إخفاء فرق.</td></tr></tbody></table></div>
				<div class="ag-report-grid"><button data-report="General Ledger"><strong>دفتر الأستاذ العام</strong><span>تتبع كل حركة مدينة ودائنة بحسب الحساب والمستند.</span></button><button data-report="Trial Balance"><strong>ميزان المراجعة</strong><span>التحقق من تساوي إجمالي المدين والدائن.</span></button><button data-report="Profit and Loss Statement"><strong>قائمة الدخل</strong><span>مراجعة الإيرادات والمصروفات ونتيجة الفترة.</span></button><button data-report="Balance Sheet"><strong>قائمة المركز المالي</strong><span>مراجعة الأصول والالتزامات وحقوق الملكية.</span></button></div>
			</section>

			<section class="ag-section" data-topic="examples" data-audience="all accountant manager" data-search="مثال تبرع صرف عهدة عملة">
				<div class="ag-section-heading"><span>10</span><div><h2>أمثلة تطبيقية</h2><p>استخدم الأنماط الآتية لاختيار المستند الصحيح وتوقع أثره المحاسبي.</p></div></div>
				<div class="ag-example-grid"><article><span>مثال أ</span><h3>تحصيل تبرع بالدولار بواسطة محصّل</h3><ol><li>تحقق من ملف المحصّل وحساب عهدة الدولار.</li><li>أنشئ المتبرع عند الحاجة دون تكرار.</li><li>أدخل سند التبرع والمشروع ومركز التكلفة.</li><li>استكمل المراجعة واعتمد السند.</li><li>القيد: مدين عهدة المحصّل، دائن إيراد التبرعات.</li></ol></article><article><span>مثال ب</span><h3>شراء ليرة لبنانية مقابل الدولار</h3><ol><li>أنشئ قيد يومية متعدد العملات.</li><li>اجعل صندوق الليرة مديناً بالمبلغ المشترى.</li><li>اجعل صندوق الدولار دائناً بالمبلغ المباع.</li><li>أدخل سعر الصرف بحيث يتوازن القيد بعملة الشركة.</li><li>راجع ظهوره في تقرير الحركة اليومية.</li></ol></article><article><span>مثال ج</span><h3>طلب عهدة لمصروف مشروع</h3><ol><li>أنشئ مذكرة دفع من نوع «عهدة».</li><li>حدد المدير والمشروع وأرفق المستندات.</li><li>استكمل مسار الموافقات.</li><li>عند الإنفاق، أنشئ إقفال عهدة مرتبطاً بالأصل.</li></ol></article><article><span>مثال د</span><h3>تصحيح قيد مرحّل</h3><ol><li>لا تعدّل الأثر المالي يدوياً.</li><li>ألغِ المستند الأصلي لإنشاء قيد عكسي.</li><li>أنشئ مستنداً مصححاً بتاريخ ترحيل مناسب.</li><li>أرفق سبب التصحيح ومرجعه.</li></ol></article></div>
			</section>

			<section class="ag-section" data-topic="approvals" data-audience="all manager" data-search="صلاحيات اعتماد إعادة رفض">
				<div class="ag-section-heading"><span>11</span><div><h2>الأدوار والصلاحيات وضوابط الاعتماد</h2><p>الاعتماد مسؤولية رقابية تؤكد سلامة الغرض والمستند والتوجيه المحاسبي، وليس إجراءً شكلياً.</p></div></div>
				<div class="ag-manager-grid"><div><h3>مقدم الطلب</h3><ul><li>يشرح الغرض بوضوح.</li><li>يرفق المستندات المؤيدة.</li><li>يصحح الملاحظات عند الإعادة.</li></ul></div><div><h3>المراجع المالي</h3><ul><li>يتحقق من الحساب والعملة ومركز التكلفة.</li><li>يراجع الرصيد والموازنة عند الحاجة.</li><li>يوثق سبب الإعادة أو الرفض.</li></ul></div><div><h3>صاحب الاعتماد</h3><ul><li>يتحقق من المشروعية والصلاحية.</li><li>لا يعتمد مستنداً ناقصاً.</li><li>يراجع التقارير اللاحقة للتنفيذ.</li></ul></div></div>
				<div class="ag-note"><strong>صياغة الملاحظة المهنية:</strong> اذكر الحقل أو المستند المطلوب، والسبب، والإجراء التصحيحي المتوقع. تجنب العبارات العامة مثل «غير صحيح».</div>
			</section>

			<section class="ag-section" data-topic="reports" data-audience="all accountant manager" data-search="تقارير حركة يومية أسبوعية شهرية خزينة">
				<div class="ag-section-heading"><span>12</span><div><h2>التقارير ومجالات استخدامها</h2><p>ابدأ بالتقرير التشغيلي المناسب، ثم انتقل إلى التقارير الدورية للتحليل والمراجعة الإدارية.</p></div></div>
				<figure class="ag-shot ag-diagram"><img src="${image_root}/reporting-map.png" alt="خريطة التقارير المحاسبية"><figcaption>خريطة تربط التقارير اليومية والأسبوعية والشهرية بهدف الرقابة ومستوى المسؤولية.</figcaption></figure>
				<div class="ag-report-grid"><button data-report="Daily Movement"><strong>الحركة اليومية</strong><span>الرصيد السابق والوارد والصادر والرصيد الحالي لكل عملة.</span></button><button data-report="Daily Treasury Report"><strong>تقرير الخزينة اليومي</strong><span>حركة حسابات الصندوق والبنوك بحسب المستند.</span></button><button data-report="Pending Accounting Approvals"><strong>الموافقات المحاسبية المعلقة</strong><span>المستندات التي تنتظر إجراءً رقابياً.</span></button><button data-report="Open Custodies"><strong>العهد المفتوحة</strong><span>العهد غير المسوّاة وأعمارها وأرصدة كل منها.</span></button><button data-report="Weekly Cash Bank Comparison"><strong>المقارنة الأسبوعية للصندوق والبنك</strong><span>تحليل تغير السيولة بين الفترات.</span></button><button data-report="Monthly Cost Center Movement"><strong>الحركة الشهرية لمراكز التكلفة</strong><span>الإيرادات والمصروفات بحسب مركز المسؤولية.</span></button></div>
			</section>

			<section class="ag-section" data-topic="closing" data-audience="all accountant manager" data-search="إقفال شهر مطابقة مراجعة">
				<div class="ag-section-heading"><span>13</span><div><h2>الإقفال الشهري المهني</h2><p>نفّذ الإقفال بتسلسل رقابي يضمن اكتمال البيانات وإمكانية إعادة إنتاج التقارير ومراجعتها.</p></div></div>
				<div class="ag-close-list"><div><b>01</b><span><strong>اكتمال المستندات</strong>رحّل المقبوضات والمدفوعات والتسليمات والتسويات الخاصة بالفترة.</span></div><div><b>02</b><span><strong>المطابقات</strong>طابق الصندوق والبنوك والعهد والذمم مع المستندات والكشوف الخارجية.</span></div><div><b>03</b><span><strong>مراجعة التحليلات</strong>راجع مراكز التكلفة والمشاريع والفروع والعملات وأسعار الصرف.</span></div><div><b>04</b><span><strong>معالجة الفروقات</strong>أنشئ قيود التصحيح المعتمدة مع مراجع واضحة.</span></div><div><b>05</b><span><strong>إصدار التقارير</strong>احفظ ميزان المراجعة وقائمة الدخل والمركز المالي وتقارير الإدارة.</span></div><div><b>06</b><span><strong>اعتماد الإقفال</strong>وثق المراجعة ثم اقفل الفترة لمنع التعديلات غير المصرح بها.</span></div></div>
			</section>

			<section class="ag-section" data-topic="troubleshooting" data-audience="all accountant manager" data-search="خطأ مشكلة صلاحية حساب شركة">
				<div class="ag-section-heading"><span>14</span><div><h2>معالجة الأخطاء</h2><p>عالج سبب الخطأ في التهيئة أو المستند الأساسي قبل تعديل بيانات المعاملة.</p></div></div>
				<details><summary>الحساب لا يظهر في قائمة الاختيار</summary><p>تحقق من الشركة، وأن الحساب تفصيلي وغير معطل، وأن عملته ملائمة للمعاملة.</p></details><details><summary>الطرف غير متاح في سند الصرف</summary><p>راجع نوع الطرف وربطه بالشركة وجدول حساباته، وتأكد من أن السجل فعّال.</p></details><details><summary>لا يمكن اعتماد المستند</summary><p>راجع حالة الموافقة ودور المستخدم والحقول الإلزامية عند الاعتماد، ثم اقرأ رسالة النظام كاملة.</p></details><details><summary>الرصيد النقدي يظهر بالسالب</summary><p>راجع اتجاه القيود الافتتاحية؛ حسابات الصندوق والبنك أصول، وتكون الزيادة فيها مدينة عادةً.</p></details><details><summary>سعر الصرف غير موجود</summary><p>أدخل سعر صرف الشركة للعملتين بتاريخ يساوي تاريخ المعاملة أو يسبقه، وتحقق من اتجاه التحويل.</p></details>
			</section>

			<section class="ag-section" data-topic="glossary" data-audience="all accountant manager" data-search="مصطلحات مدين دائن عهدة ترحيل">
				<div class="ag-section-heading"><span>15</span><div><h2>المصطلحات المحاسبية</h2><p>توحيد المصطلحات يقلل أخطاء الدورة المستندية والتقارير.</p></div></div>
				<div class="ag-glossary"><div><strong>مدين</strong><span>الطرف الأيسر من القيد؛ تزيد به الأصول والمصروفات عادةً.</span></div><div><strong>دائن</strong><span>الطرف الأيمن من القيد؛ تزيد به الالتزامات والإيرادات عادةً.</span></div><div><strong>عهدة</strong><span>مبلغ تحت مسؤولية شخص إلى حين التسليم أو التسوية.</span></div><div><strong>مركز التكلفة</strong><span>بعد تحليلي لقياس الإيرادات والمصروفات بحسب المسؤولية أو النشاط.</span></div><div><strong>تاريخ الترحيل</strong><span>التاريخ الذي يظهر فيه الأثر المالي في دفتر الأستاذ.</span></div><div><strong>قيد عكسي</strong><span>قيد يلغي أثر مستند معتمد مع الحفاظ على مسار التدقيق.</span></div><div><strong>عملة الشركة</strong><span>العملة الأساسية لإعداد الدفاتر والقوائم المالية.</span></div><div><strong>المستند المؤيد</strong><span>فاتورة أو إيصال أو عقد يثبت سبب المعاملة وقيمتها.</span></div><div><strong>الرصيد القائم</strong><span>المبلغ الذي لم يُسدّد أو يُسلّم أو يُسوّ بعد.</span></div></div>
			</section>

			<footer class="ag-footer"><strong>المحاسبة السليمة تبدأ بمستند مكتمل وقابل للمراجعة.</strong><span>عند وجود نقص، أعد المستند بملاحظة دقيقة ولا تتجاوز مسار الصلاحيات.</span></footer>
			<div class="ag-empty" hidden>لا توجد موضوعات مطابقة لعبارة البحث.</div>
		</div>`;
};
