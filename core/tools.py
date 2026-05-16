"""
JARVIS araç tanımları — Gemini Live function declarations.
Alp Ünlü tarafından yapılmıştır — @alppunlu

Android port: macOS sürümündeki araçların aynısı; yalnızca platforma özel
açıklamalar Android'e uyarlandı. shell_run aracı kaldırıldı çünkü Android'de
genel bir terminal/kabuk erişimi için güvenli ve denenebilir bir karşılık yok.
"""

TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": "Android'de herhangi bir uygulamayı açar. Spotify, Chrome, WhatsApp, YouTube, Ayarlar vb.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Uygulama adı (örn. 'Spotify', 'Chrome', 'WhatsApp')",
                }
            },
            "required": ["app_name"],
        },
    },
    {
        "name": "sys_info",
        "description": "Sistem bilgisi alır: pil durumu, CPU, RAM, depolama, saat, tarih, ağ bağlantısı.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "battery | cpu | ram | disk | time | date | network | all",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_weather",
        "description": (
            "Anlik hava durumunu ozetler. Varsayilan konum Istanbul'dur. "
            "Kullanici hava durumunu, sicakligi veya yagmur durumunu sordugunda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "location": {
                    "type": "STRING",
                    "description": "Sehir veya konum. Bos birakilirsa Istanbul kullanilir.",
                }
            },
        },
    },
    {
        "name": "get_calendar_events",
        "description": (
            "Cihazin takvimini okur. "
            "Bugun, yarin, siradaki etkinlik veya yaklasan ajandayi ozetler. "
            "Kullanici toplanti, takvim, ajanda, etkinlik veya gunluk programini sordugunda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": (
                        "today | tomorrow | next | agenda | week veya dogal dilde "
                        "'onumuzdeki 30 gun', '2 hafta', 'bu ay', 'gelecek ay'"
                    ),
                },
                "limit": {"type": "NUMBER", "description": "Maksimum etkinlik sayisi"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "add_calendar_event",
        "description": (
            "Cihazin takvimine yeni etkinlik ekler. "
            "Kullanici toplanti, randevu, takvime ekleme veya etkinlik olusturma isterse kullan. "
            "Baslangic tarihini gercek tarih/saat olarak ver; bitis verilmezse varsayilan sure kullanilir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING", "description": "Etkinlik basligi. Ornek: 'Disci Randevusu'"},
                "start_iso": {"type": "STRING", "description": "Baslangic tarih/saat. ISO veya yyyy-MM-dd HH:mm formatinda."},
                "end_iso": {"type": "STRING", "description": "Bitis tarih/saat. Opsiyonel."},
                "location": {"type": "STRING", "description": "Etkinlik konumu. Opsiyonel."},
                "notes": {"type": "STRING", "description": "Etkinlik notlari. Opsiyonel."},
                "calendar_name": {"type": "STRING", "description": "Eklenecek takvim adi. Opsiyonel."},
                "all_day": {"type": "BOOLEAN", "description": "true ise tum gun etkinligi olusturur."},
            },
            "required": ["title", "start_iso"],
        },
    },
    {
        "name": "delete_calendar_event",
        "description": (
            "Cihazin takviminden etkinlik siler. "
            "Kullanici bir toplantiyi, randevuyu veya takvim kaydini silmek istediginde kullan. "
            "Ayni ada birden fazla etkinlik varsa dogru kaydi bulmak icin baslangic tarihini gercek tarih/saat olarak ver."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING", "description": "Silinecek etkinlik basligi. Ornek: 'Disci Randevusu'"},
                "start_iso": {"type": "STRING", "description": "Opsiyonel tarih/saat. Ayni isimli birden fazla etkinligi ayirt etmek icin kullan."},
                "calendar_name": {"type": "STRING", "description": "Opsiyonel takvim adi"},
                "delete_all_matches": {"type": "BOOLEAN", "description": "true ise eslesen tum etkinlikleri siler"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "get_reminders",
        "description": (
            "Animsaticilari okur. "
            "Bugunku, yaklasan, geciken veya tum acik animsaticilari ozetler. "
            "Kullanici hatirlatma, animsatici, reminder veya yapilacaklar listesini sordugunda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "today | upcoming | overdue | all | next"},
                "limit": {"type": "NUMBER", "description": "Maksimum animsatici sayisi"},
                "list_name": {"type": "STRING", "description": "Istenirse belirli bir animsatici listesi adi"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "add_reminder",
        "description": (
            "Yeni bir animsatici ekler (cihaz takvimine alarm/bildirim olarak yazilir). "
            "Kullanici 'hatirlat', 'animsatici ekle', 'reminder kur' dediginde kullan. "
            "Goreli zaman ifadelerini bugunku tarih baglamina gore due_iso alanina ISO formatinda cevir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING", "description": "Animsatici basligi"},
                "due_iso": {"type": "STRING", "description": "Opsiyonel tarih/saat. Ornek: 2026-04-13T09:00 veya tum gun icin 2026-04-13"},
                "notes": {"type": "STRING", "description": "Opsiyonel not"},
                "list_name": {"type": "STRING", "description": "Opsiyonel animsatici listesi"},
                "priority": {"type": "STRING", "description": "low | medium | high"},
                "all_day": {"type": "BOOLEAN", "description": "Tum gun animsatici ise true"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "browser_control",
        "description": "Tarayıcıda URL açar, Google'da arama yapar veya YouTube'da ilk sonucu doğrudan oynatır.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "open_url | search | play_youtube"},
                "url": {"type": "STRING", "description": "Açılacak URL (open_url için)"},
                "query": {"type": "STRING", "description": "Arama sorgusu (search veya play_youtube için)"},
            },
            "required": ["action"],
        },
    },
    {
        "name": "play_media",
        "description": (
            "YouTube, Spotify veya Apple Music uygulamasında şarkı, müzik veya video açar. "
            "Kullanıcı belirli bir platform söylerse onu kullan. "
            "Belirtmezse uygun olanı dene. "
            "Kullanıcı 'çal', 'oynat', 'aç' diyorsa autoplay=true kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Şarkı, sanatçı, albüm veya video arama ifadesi"},
                "provider": {"type": "STRING", "description": "auto | youtube | spotify | apple_music"},
                "autoplay": {"type": "BOOLEAN", "description": "true ise mümkünse doğrudan oynatır"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_youtube_channel_report",
        "description": (
            "YouTube kanalinin public istatistiklerini ve son videolarin performansini raporlar. "
            "Kullanici kanal istatistiklerini, abone sayisini, son videolarini, buyume hizini "
            "veya YouTube analizini sordugunda kullan. Bu arac Studio yerine public YouTube Data API verisini kullanir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": (
                        "Dogal dilde analiz istegi. Ornek: "
                        "'YouTube istatistiklerim nasil', 'son videolarimi analiz et', "
                        "'kanal buyumemi ozetle'"
                    ),
                },
                "handle": {
                    "type": "STRING",
                    "description": (
                        "Opsiyonel kanal handle'i, kanal linki veya kanal ID'si. "
                        "Bos birakilirsa ayarlardaki youtube_channel_handle kullanilir."
                    ),
                },
                "video_limit": {"type": "NUMBER", "description": "Analize dahil edilecek son video sayisi. Varsayilan 6."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "analyze_screen",
        "description": (
            "Cihazin o anki ekran goruntusunu alip Gemini vision ile analiz eder. "
            "Kullanici ekranda ne oldugunu, bir hatayi, gorunen metni, butonlari veya ekran icerigini sordugunda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Kullanicinin ekranla ilgili sorusu. Ornek: 'Bu hatayi oku', 'Ekranda ne var?'",
                },
                "target": {"type": "STRING", "description": "Su an sadece active_window desteklenir."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "save_memory",
        "description": "Kullanıcı hakkında önemli bilgiyi kalıcı belleğe kaydeder. İsim, tercihler, projeler vb. duyunca sessizce çağır.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {"type": "STRING", "description": "identity | preferences | projects | notes"},
                "key": {"type": "STRING", "description": "Kısa anahtar (örn. 'name')"},
                "value": {"type": "STRING", "description": "Değer (İngilizce)"},
            },
            "required": ["category", "key", "value"],
        },
    },
    {
        "name": "delete_memory",
        "description": (
            "Kalici hafizadaki bir kaydi siler. "
            "Kullanici 'bunu hafizandan kaldir', 'unut', 'sil' gibi bir sey derse kullan. "
            "Mumkunse category ve key ile sil; emin degilsen match_text ile ilgili kaydi bulup kaldir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {"type": "STRING", "description": "Kaydin kategorisi. Ornek: notes | identity | preferences | projects"},
                "key": {"type": "STRING", "description": "Silinecek anahtar. Ornek: claude_limit_refresh"},
                "match_text": {"type": "STRING", "description": "Kaydi bulmak icin kullanilacak dogal dil parcasi."},
            },
        },
    },
    {
        "name": "send_whatsapp_message",
        "description": (
            "WhatsApp üzerinden mesaj taslağı açar. "
            "Kişi adı veya telefon numarasıyla çalışabilir. "
            "Telefon numarası verilmemişse kişi adını önce kayıtlı WhatsApp kişileri ve içe aktarılan telefon rehberinde ara. "
            "Android güvenlik modeli otomatik göndermeye izin vermediği için mesaj, alıcının sohbeti "
            "önceden doldurularak açılır; kullanıcı tek dokunuşla gönderir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "recipient_name": {"type": "STRING", "description": "Kişi adı. Örn: 'Anne', 'Ahmet', 'Ece'"},
                "phone_number": {"type": "STRING", "description": "Uluslararası telefon numarası. Örn: +905551112233"},
                "message": {"type": "STRING", "description": "Gönderilecek mesaj içeriği"},
                "app_target": {"type": "STRING", "description": "desktop | web | auto. Android'de her zaman WhatsApp uygulaması kullanılır."},
                "send_now": {"type": "BOOLEAN", "description": "true ise sohbet mesaj hazır halde açılır"},
            },
            "required": ["message"],
        },
    },
    {
        "name": "save_whatsapp_contact",
        "description": (
            "Sık kullanılan bir WhatsApp kişisini adı ve telefon numarasıyla kalıcı belleğe kaydeder. "
            "Kullanıcı bir kişiyi 'annem', 'Ahmet', 'iş ortağım' gibi tekrar kullanılacak şekilde tanımladığında kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "display_name": {"type": "STRING", "description": "Kaydedilecek kişi adı. Örn: 'Annem', 'Ahmet'"},
                "phone_number": {"type": "STRING", "description": "Uluslararası telefon numarası. Örn: +905551112233"},
                "aliases": {"type": "STRING", "description": "Virgülle ayrılmış alternatif hitaplar. Örn: 'anne, annem, mom'"},
            },
            "required": ["display_name", "phone_number"],
        },
    },
]
