// src/data/coursesData.ts
import type { SubtitleItem } from "../utils/srtParser";

export interface VideoCourseDetail {
  id: string;
  title: string;
  description: string;
  level: "A1" | "A2" | "B1" | "B2" | "C1";
  duration: string;
  sentenceCount: number;
  progressPercentage: number;
  thumbnailUrl: string;
  videoUrl: string;
  subtitles: SubtitleItem[];
}

export const COURSES_DATA: Record<string, VideoCourseDetail> = {
  "1": {
    id: "1",
    title: "مکالمه روزمره و انگیزش شغلی",
    description: "تمرین گفتار و تلفظ روی جملات پرکاربرد مکالمات کاری و انگیزش شغلی.",
    level: "B1",
    duration: "02:45",
    sentenceCount: 3,
    progressPercentage: 65,
    thumbnailUrl: "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?q=80&w=600&auto=format&fit=crop",
    videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
    subtitles: [
      { id: 1, startTime: 0, endTime: 3.5, text: "Yes, you can achieve all your goals." },
      { id: 2, startTime: 3.6, endTime: 7.2, text: "Consistency is the key to mastering pronunciation." },
      { id: 3, startTime: 7.3, endTime: 11.0, text: "Let's focus on rhythm and sentence stress." },
    ],
  },
  "2": {
    id: "2",
    title: "اصطلاحات انیمیشن و سینما",
    description: "یادگیری لحن طبیعی و استرس کلمات در مکالمات روان سینمایی.",
    level: "A2",
    duration: "01:30",
    sentenceCount: 2,
    progressPercentage: 20,
    thumbnailUrl: "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?q=80&w=600&auto=format&fit=crop",
    videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
    subtitles: [
      { id: 1, startTime: 0, endTime: 4.0, text: "I am going to make him an offer he cannot refuse." },
      { id: 2, startTime: 4.1, endTime: 8.0, text: "Keep your friends close, but your enemies closer." },
    ],
  },
  "3": {
    id: "3",
    title: "سخنرانی‌های تخصصی و آکادمیک",
    description: "تمرین ریتم گفتار، زیروبمی صدا (Pitch) و فونم‌های پیشرفته زبان انگلیسی.",
    level: "C1",
    duration: "05:10",
    sentenceCount: 1,
    progressPercentage: 0,
    thumbnailUrl: "https://images.unsplash.com/photo-1475721027785-f74eccf877e2?q=80&w=600&auto=format&fit=crop",
    videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4",
    subtitles: [
      { id: 1, startTime: 0, endTime: 5.0, text: "Artificial intelligence is transforming modern linguistics." },
    ],
  },
};