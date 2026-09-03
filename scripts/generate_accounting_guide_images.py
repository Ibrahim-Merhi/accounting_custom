#!/usr/bin/env python3
import html
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "accounting_custom/public/images/accounting_guide/ar"


BASE_CSS = """
*{box-sizing:border-box}body{margin:0;background:#f4f7fa;color:#172033;font-family:Tahoma,Arial,sans-serif;direction:rtl}
.canvas{width:1600px;height:900px;padding:44px;background:#f4f7fa}.window{height:100%;overflow:hidden;border:1px solid #d6dde6;border-radius:10px;background:#fff;box-shadow:0 16px 42px rgba(23,32,51,.12)}
.top{height:64px;display:flex;align-items:center;justify-content:space-between;padding:0 28px;border-bottom:1px solid #e2e7ed}.brand{font-size:21px;font-weight:700}.crumb{color:#667085}.body{display:flex;height:calc(100% - 64px)}
.side{width:270px;padding:24px 18px;border-left:1px solid #e2e7ed;background:#fafbfc}.side h3{margin:0 12px 16px;font-size:13px;color:#667085}.nav{padding:11px 14px;margin:5px 0;border-radius:7px;font-size:16px}.nav.active{background:#e8f1ff;color:#1859b7;font-weight:700}
.main{flex:1;padding:30px 38px}.title{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px}.title h1{margin:0;font-size:27px}.badge{padding:6px 11px;border-radius:16px;background:#e9f8ef;color:#18794e;font-size:12px}
.callout{position:relative;border:2px solid #2563eb;border-radius:9px}.pin{position:absolute;display:grid;place-items:center;width:40px;height:40px;border-radius:50%;background:#1565c0;color:#fff;font-size:20px;font-weight:700}.note{padding:13px 18px;border:2px solid #2563eb;border-radius:8px;background:#fff;color:#123c72;font-weight:700}
.cards{display:flex;flex-wrap:wrap;margin:0 -9px}.card{width:31%;min-height:190px;margin:0 1.16% 18px;padding:20px;border:1px solid #dce2e9;border-radius:8px;background:#fff}.card h2{margin:0 0 14px;font-size:18px}.card div{padding:7px 0;color:#4e5b6a}
.flow{display:flex;align-items:center;justify-content:center;gap:12px;height:520px}.step{width:220px;min-height:220px;padding:24px 16px;border:1px solid #d9e1ea;border-top:5px solid #2563eb;border-radius:8px;background:#fff;text-align:center;overflow:hidden}.step b{display:grid;place-items:center;width:42px;height:42px;margin:0 auto 16px;border-radius:50%;background:#1d4f91;color:#fff;font-size:20px}.step h2{font-size:18px}.step p{height:72px;overflow:hidden;color:#667085;font-size:13px;line-height:1.7;white-space:normal}.arrow{color:#7d8b99;font-size:28px}
.form-grid{display:flex;margin:0 -8px}.field{flex:1;margin:0 8px}.field label{display:block;margin-bottom:6px;color:#586577;font-size:13px}.input{height:43px;padding:11px;border:1px solid #cfd7e1;border-radius:6px;background:#fafbfc}.table{margin-top:28px;border:1px solid #d5dde6;border-radius:7px;overflow:hidden}.row{display:flex}.row>div{padding:12px;border-left:1px solid #e1e6eb}.row>div:nth-child(1){width:24%}.row>div:nth-child(2){width:26%}.row>div:nth-child(3){width:20%}.row>div:nth-child(4),.row>div:nth-child(5){width:15%}.row.head{background:#edf1f4;font-weight:700}.row.data{color:#53606e}
.report-grid{display:flex;flex-wrap:wrap;margin:55px -11px 0}.report{width:31%;min-height:170px;margin:0 1.16% 22px;padding:22px;border:1px solid #d9e0e8;border-radius:8px;background:#fff}.report h2{margin:0 0 11px;color:#1d4f91;font-size:19px}.report p{color:#667085;line-height:1.8}.footer-note{margin-top:25px;padding:16px 20px;border-right:5px solid #e5a000;background:#fff8df;color:#6d5410;overflow:hidden}
"""


def page(title, content, subtitle="الدليل التشغيلي للمحاسبة"):
	return f"""<!doctype html><html lang="ar"><head><meta charset="utf-8"><style>{BASE_CSS}</style></head><body><div class="canvas"><div class="window"><div class="top"><div class="brand">نظام المحاسبة</div><div class="crumb">{subtitle}</div></div>{content}</div></div></body></html>"""


def workflow(title, steps, note):
	items = []
	for index, (heading, text) in enumerate(steps, 1):
		items.append(f'<div class="step"><b>{index}</b><h2>{html.escape(heading)}</h2><p>{html.escape(text)}</p></div>')
		if index < len(steps):
			items.append('<div class="arrow">←</div>')
	return page(title, f'<div class="main"><div class="title"><h1>{html.escape(title)}</h1><span class="badge">مسار معتمد</span></div><div class="flow">{"".join(items)}</div><div class="footer-note">{html.escape(note)}</div></div>')


PAGES = {
	"accounting-workspace-overview.png": page("مساحة عمل المحاسبة", """
		<div class="body"><aside class="side"><h3>مساحات العمل</h3><div class="nav">الرئيسية</div><div class="nav active">المحاسبة</div><div class="nav">إدارة الإغاثة</div><div class="nav">الموارد البشرية</div><div class="nav">المشتريات</div></aside><main class="main"><div class="title"><h1>المحاسبة</h1><span class="badge">الشركة: الاتحاد</span></div><div class="cards"><section class="card"><h2>التبرعات والمحصّلون</h2><div>سند التبرع</div><div>ملف المحصّل</div><div>تسليم المحصّل</div></section><section class="card"><h2>المدفوعات والعهد</h2><div>سند الصرف المحاسبي</div><div>مذكرة الدفع</div><div>العهد المفتوحة</div></section><section class="card"><h2>تقارير الخزينة</h2><div>الحركة اليومية</div><div>تقرير الخزينة اليومي</div><div>الموافقات المعلقة</div></section><section class="card"><h2>التهيئة المحاسبية</h2><div>دليل الحسابات</div><div>مراكز التكلفة</div><div>أسعار الصرف</div></section><section class="card"><h2>التقارير الدورية</h2><div>ميزان المراجعة</div><div>قائمة الدخل</div><div>قائمة المركز المالي</div></section></div><div class="footer-note">ابدأ من بطاقة العملية المطلوبة، ثم استخدم التقارير للتحقق من أثرها بعد الاعتماد.</div></main></div>"""),
	"accounting-payment-entry.png": page("سند الصرف المحاسبي", """
		<div class="main"><div class="title"><h1>سند صرف محاسبي جديد</h1><span class="badge">مسودة</span></div><div class="form-grid"><div class="field"><label>الشركة</label><div class="input">الاتحاد</div></div><div class="field"><label>تاريخ الترحيل</label><div class="input">2026-09-03</div></div><div class="field"><label>الفرع</label><div class="input">المركز الرئيسي</div></div></div><div class="table"><div class="row head"><div>طريقة الدفع</div><div>الحساب</div><div>مركز التكلفة</div><div>العملة</div><div>المبلغ</div></div><div class="row data"><div>صندوق الدولار</div><div>مصروفات المشروع</div><div>المشروع العام</div><div>USD</div><div>1,000.00</div></div><div class="row data"><div>صندوق الليرة</div><div>مساعدات نقدية</div><div>برنامج الإغاثة</div><div>LBP</div><div>50,000,000</div></div></div><div class="footer-note">يمكن حفظ المسودة قبل استكمال الحساب ومركز التكلفة، لكنهما إلزاميان قبل الاعتماد.</div></div>"""),
	"donation-custody-workflow.png": workflow("دورة التبرع وعهدة المحصّل", [("ملف المحصّل", "حساب عهدة مستقل لكل عملة"), ("سند التبرع", "المتبرع والمبلغ والمشروع"), ("المراجعة المالية", "المستند والتوجيه المحاسبي"), ("تسليم المحصّل", "النقل إلى الصندوق أو البنك")], "لا يُعد المبلغ مسلّماً للخزينة قبل اعتماد مستند تسليم المحصّل."),
	"payment-memo-workflow.png": workflow("مسار اعتماد مذكرة الدفع", [("مقدم الطلب", "الغرض والمستندات المؤيدة"), ("المدير المسؤول", "الحاجة والموازنة"), ("الشؤون المالية", "الحساب ومركز التكلفة"), ("الرئيس", "اعتماد الصرف"), ("أمين الصندوق", "تنفيذ الدفع وتوثيقه")], "تعاد المذكرة للتصحيح عند وجود نقص، بينما يوقف الرفض مسار الطلب."),
	"payroll-cycle.png": workflow("الدورة المحاسبية الشهرية للرواتب", [("تثبيت الاستحقاقات", "هيكل الراتب والتعيينات"), ("توزيع التكلفة", "مراكز التكلفة بنسبة 100%"), ("الحسميات الشهرية", "الحسميات ومستنداتها"), ("مراجعة السجل", "المراجعة النهائية قبل الدفع")], "لا يُنفذ دفع الرواتب قبل معالجة الملاحظات واعتماد سجل الرواتب النهائي."),
	"reporting-map.png": page("خريطة التقارير المحاسبية", """
		<div class="main"><div class="title"><h1>التقارير بحسب دورية المراجعة</h1><span class="badge">رقابة وإدارة</span></div><div class="report-grid"><section class="report"><h2>يومياً</h2><p>الحركة اليومية<br>تقرير الخزينة اليومي<br>الموافقات المحاسبية المعلقة</p></section><section class="report"><h2>أسبوعياً</h2><p>مقارنة الصندوق والبنك<br>مقارنة مراكز التكلفة<br>متابعة العهد والتسليمات</p></section><section class="report"><h2>شهرياً</h2><p>حركة مراكز التكلفة<br>الرصيد النقدي والمصرفي<br>ملخص تبرعات المشاريع</p></section><section class="report"><h2>القوائم المالية</h2><p>ميزان المراجعة<br>قائمة الدخل<br>قائمة المركز المالي</p></section><section class="report"><h2>المراجعة الإدارية</h2><p>تحليل الفروقات<br>مراجعة الموازنات<br>توثيق إجراءات التصحيح</p></section></div><div class="footer-note">يجب أن ينتقل المراجع من المستند إلى دفتر الأستاذ، ثم إلى التقرير الدوري والقائمة المالية.</div></div>"""),
}


def main():
	OUTPUT.mkdir(parents=True, exist_ok=True)
	with tempfile.TemporaryDirectory() as temporary_directory:
		temporary = Path(temporary_directory)
		for filename, markup in PAGES.items():
			source = temporary / f"{filename}.html"
			source.write_text(markup, encoding="utf-8")
			destination = OUTPUT / filename
			subprocess.run([
				"wkhtmltoimage", "--quiet", "--width", "1600", "--height", "900",
				"--quality", "92", str(source), str(destination),
			], check=True)
			with Image.open(destination) as image:
				image.convert("RGB").save(destination, optimize=True)


if __name__ == "__main__":
	main()
