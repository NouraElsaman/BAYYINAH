"use client";

import Link from "next/link";
import { BookOpen, Calendar, Clock, ChevronLeft, ArrowRight, Tag } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const BLOG_POSTS = [
  {
    id: 1,
    title: "آخر تعديلات قانون العمل المصري 2026: ما تحتاج لمعرفته",
    description:
      "شرح تفصيلي للتعديلات التشريعية الجديدة المتعلقة بساعات العمل، الإجازات السنوية، وحقوق العمال عند إنهاء الخدمة.",
    date: "٤ يوليو ٢٠٢٦",
    readTime: "٥ دقائق",
    category: "قانون العمل",
    slug: "egypt-labor-law-updates-2026",
  },
  {
    id: 2,
    title: "كيفية صياغة عقد الإيجار الجديد بشكل يحميك من النزاعات",
    description:
      "دليلك الشامل لصياغة البنود الأساسية والشروط الجزائية في عقود الإيجار السكنية والتجارية طبقاً للقانون رقم ٤ لسنة ١٩٩٦.",
    date: "٢٠ يونيو ٢٠٢٦",
    readTime: "٧ دقائق",
    category: "القانون المدني",
    slug: "how-to-draft-rental-contracts-egypt",
  },
  {
    id: 3,
    title: "شروط وضوابط فسخ العقود تلقائياً في القانون المدني المصري",
    description:
      "متى يعتبر العقد مفسوخاً من تلقاء نفسه دون الحاجة لحكم قضائي؟ دراسة قانونية مبسطة للشرط الفاسخ الصريح.",
    date: "١٠ يونيو ٢٠٢٦",
    readTime: "٦ دقائق",
    category: "القانون المدني",
    slug: "contract-termination-conditions-egypt",
  },
  {
    id: 4,
    title: "حقوق المستأجر والمالك في ترميم العين المؤجرة وصيانتها",
    description:
      "من يتحمل تكاليف صيانة السباكة والكهرباء والترميمات الأساسية؟ توضيح للمادة ٥٦٧ من القانون المدني المصري.",
    date: "١ يونيو ٢٠٢٦",
    readTime: "٤ دقائق",
    category: "قوانين الإيجار",
    slug: "tenant-landlord-maintenance-rights",
  },
  {
    id: 5,
    title: "الحماية القانونية للبيانات الشخصية بمصر: دليل الشركات الناشئة",
    description:
      "خطوات عملية للامتثال لقانون حماية البيانات الشخصية رقم ١٥١ لسنة ٢٠٢٠ لتجنب العقوبات والغرامات المالية.",
    date: "١٥ مايو ٢٠٢٦",
    readTime: "٨ دقائق",
    category: "قوانين التكنولوجيا",
    slug: "data-privacy-law-egypt-startups",
  },
  {
    id: 6,
    title: "جرائم النصب الإلكتروني في قانون مكافحة جرائم تقنية المعلومات",
    description:
      "كيف يحميك القانون المصري رقم ١٧٥ لسنة ٢٠١٨ من الاحتيال الرقمي؟ وما هي الإجراءات القانونية المتبعة للبلاغ؟",
    date: "٥ مايو ٢٠٢٦",
    readTime: "٦ دقائق",
    category: "القانون الجنائي",
    slug: "cybercrime-law-egypt",
  },
];

export default function BlogPage() {
  return (
    <main className="px-3 sm:px-4 md:px-6 lg:px-8 py-8 sm:py-10 max-w-7xl mx-auto pb-24 text-right">

      {/* Page Header */}
      <header className="mb-8 sm:mb-12 border-b border-border/40 pb-6 sm:pb-8">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold flex items-center justify-end gap-2 text-foreground">
              المدونة القانونية
              <BookOpen className="h-7 w-7 sm:h-8 sm:w-8 text-accent shrink-0" aria-hidden="true" />
            </h1>
            <p className="text-muted-foreground text-sm mt-2 max-w-xl">
              شروحات وتحليلات مبسطة لأحدث القوانين والأنظمة والتشريعات والقضايا الشائعة بمصر.
            </p>
          </div>
          <Button asChild variant="outline" className="rounded-xl self-start sm:self-auto gap-2 shrink-0">
            <Link href="/" aria-label="العودة إلى الصفحة الرئيسية">
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
              العودة للرئيسية
            </Link>
          </Button>
        </div>
      </header>

      {/* Articles Grid — h-full on cards for equal heights */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 sm:gap-6 lg:gap-8">
        {BLOG_POSTS.map((post) => (
          <article key={post.id} className="flex">
            <Card className="flex flex-col w-full hover:-translate-y-1 hover:shadow-md transition-all duration-300">
              <CardContent className="p-5 sm:p-6 flex flex-col flex-1">

                {/* Meta row */}
                <div className="flex items-center justify-between text-xs text-muted-foreground mb-3">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                    {post.readTime} قراءة
                  </span>
                  <time className="flex items-center gap-1" dateTime={post.slug}>
                    <Calendar className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                    {post.date}
                  </time>
                </div>

                {/* Category badge */}
                <Badge
                  variant="outline"
                  className="text-xs bg-accent/5 text-accent border-accent/20 w-fit mb-3 gap-1"
                >
                  <Tag className="h-3 w-3" aria-hidden="true" />
                  {post.category}
                </Badge>

                {/* Title */}
                <h2 className="font-bold text-base sm:text-lg text-foreground hover:text-accent transition-colors leading-snug mb-2">
                  <Link href={`/blog/${post.slug}`} aria-label={`اقرأ المقال: ${post.title}`}>
                    {post.title}
                  </Link>
                </h2>

                {/* Description — pushes "read more" to bottom */}
                <p className="text-sm text-muted-foreground leading-relaxed line-clamp-3 flex-1">
                  {post.description}
                </p>

                {/* Read More — pinned to bottom */}
                <div className="pt-4 border-t border-border/40 mt-4">
                  <Link
                    href={`/blog/${post.slug}`}
                    className="flex items-center justify-end gap-1 text-accent font-semibold text-sm hover:underline"
                    aria-label={`اقرأ المقال كاملاً: ${post.title}`}
                  >
                    اقرأ المقال كاملاً
                    <ChevronLeft className="h-4 w-4 shrink-0" aria-hidden="true" />
                  </Link>
                </div>

              </CardContent>
            </Card>
          </article>
        ))}
      </div>

    </main>
  );
}
