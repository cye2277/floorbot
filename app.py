import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
import openai
import os
import psycopg2
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# ======== 1. 環境變數設定 ========
# 請將這些值設定成你自己的金鑰
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


# PostgreSQL 連線參數
DB_PARAMS = {
    'host': os.getenv("DB_HOST"),
    'port': os.getenv("DB_PORT"),
    'dbname': os.getenv("DB_NAME"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD")
}

def init_db():
    conn = psycopg2.connect(**DB_PARAMS)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_logs (
            id SERIAL PRIMARY KEY,
            timestamp TEXT,
            user_id TEXT,
            user_message TEXT,
            bot_reply TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()


line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

# ======== 2. 模擬地板產品資料 ========
# floor_data = [
#     {"model": "DF-1001", "color": "淺木色", "waterproof": True, "price": 850, "thickness": 12},
#     {"model": "DF-1002", "color": "深木色", "waterproof": False, "price": 650, "thickness": 8},
#     {"model": "DF-1003", "color": "灰色", "waterproof": True, "price": 990, "thickness": 10}
# ]

knowledge_text = """
【公司願景﹠關於我們】
公司願景：Floors for living 為了豐富生活而生産製作的地板，要讓所有安裝地板的客戶，裝修更環保，家居更漂亮，享受優質的愜意生活！

詮倫企業股份有限公司是德國Kronotex地板在台灣的專業地板銷售公司。公司一系列引進德國Kronotex最新的產品。木地板從德國工廠直接到專賣店，沒有中間環節，價格實惠，力求台灣的消費者能得到與歐洲同步的地板產品，享受優質的家居生活。為了更好服務台灣的市場,公司另外成立翔騰國際建材有限公司、佳騰國際建材有限公司、喬思國際有限公司等關係企業，並在高雄台糖物流園區和台北五股華捷設立了物流倉儲，直接對台灣的Kronotex專賣店供貨，給客戶提供更為優質和快捷的服務。

基於對客戶全方位的服務，公司引進台灣首家Kronotex地板專賣店，讓客戶能在第一時間接觸到德國生產、原裝進口的環保優質超耐磨木地板。讓客戶能實際感受到，看到德國Kronotex各個系列的優質產品－買的稱心；用的放心。公司也將陸續在台灣各個主要縣市，結合有著相同理念，有環保意識的先進設立Kronotex專賣店，更好的服務每位台灣消費者。

維持森林的持續發展，更加合理經濟、有效的利用和研發世界森林資源，是德國高能得思地板一直以來秉持的理念。詮倫企業股份有限公司堅信經濟、生態、社會責任是三個不可分的概念。只有對社會有責任感的企業，才會帶給客戶更好的服務.
高能得思：高能得思是來自德國的地板品牌，以防水、耐磨、設計多樣著稱，產品包含強化木地板、SPC石塑地板與100%防水地板。

【德國總公司】
德國kronotex木業集團始建於1897年，公司總部位於德國柏林與漢堡之間勃蘭登堡州。是目前世界上規模最大、設備最先進的超耐磨木地板製造企業之一，年產量6000萬平方米，為世界上一百多個國家生產超耐磨地板。
一個跨越三個世紀的企業，經過一百多年磨煉，秉承卓越的傳統、雄厚的實力、先進的工藝、嚴格的環保標準和優秀的人文素質，打造出世界木材加工企業的航母，這就是德國kronotex木業集團。德國kronotex企業集團有著悠久的木材加工業歷史，是歐洲最大的超耐磨地板生產廠商，歷經漫長的歲月，始終在行業中居於領先地位，正如科隆大教堂在歐洲建築史中的成就和地位。
值得一提的是，在將歐洲最時尚的花式推進東方市場的同時，充分考慮到各種消費層次的需求，KRONOTEX擁有8mm 超高密度10mm 12mm超耐磨木地板，可供地熱供暖使用，物超所值，是性價比極佳的超耐磨木地板。KRONOTEX一貫堅持可持續發展戰略，保證市場供應的穩定性，同時將歐洲最時尚、最先進、最流行的產品源源不斷地引入東方市場
集團始終貫徹“全程操控”的原則，從林木的經營培育，到最終產品的製造都在集團的直接掌控之下，確保每一片地板產品都符合歐洲最高標準。在注重人居住環境的同時，集團最早獲得了歐洲最高環保標準“藍天使”認證，發起創建了“歐洲超耐磨木地板生產商協會（EPLF）”，並擔任該協會的常務副主席，組織並通過了高於歐洲質量標準的德國超耐磨木地板最高質量認證（RAL）。讓消費者買的放心，用的舒心。


【客戶評論】
1.台北內湖設計建材中心直營門市
鄭郁珠 ★★★★★
因為有過一次合作的經驗 第二次裝修依然選擇高能得思的產品 門市陳衣凡小姐認真負責的敬業態度 顏良安師傅專業精湛的木地板技藝 都是我再次回購的主因 優質的員工值得鼓勵 信任就是最佳的銷售

Leslie Kuo ★★★★★
好評： 品質, 守時, 專業度, 積極回應
為了搭配前屋主的地板找了很久，網路問了很多店家，最後因想看實體因緣際會走進這家品牌，Denny業務不會給人有壓力很隨和而且真誠的建議，就算問很多問題也耐心回答。他們搭配的師傅很不錯，有日本人的施工精神，很細心認真，施工過程很放心。Denny服務很好很專業，建議可以找他評估。

dennis rom ★★★★★
好評： 品質, 專業度
思樂推薦的木地板品質真的很好，完全符合我的期望我也要感謝施工人員的專業和耐心，他們在安裝過程中表現出色我家煥然一新，特別是我的孩子和妻子對新地板非常喜愛我會毫不猶豫地推薦給我的親朋好友。

2.台北內湖特力家居直營門市
巫小君 ★★★★★
為了改造舊房子的地板，比較了很多家木地板，來到高能德思遇到鄧小姐很細心又仔細的介紹，找了許多完工照片和拼法讓我了解，和家人討論之後決定下訂，成品比照片更好看，非常感謝她耐心的說明

看見台灣 ★★★★★
感謝熱心凱西的解說，我買的是高山貝格橡木，質感體驗極佳，直覺上對精神有極大的幫助，能療癒心靈，家庭成員都說好，已經是連續追買了，大推值得信賴

yingju liao ★★★★★
老公找到地板評價最好的德國高能得思地板 我們到內湖店剛好是凱西小姐服務我們的 不會因為我們施工的範圍很小 而隨便招待 整個在討論以及建議上都非常的實在 因為我們沒有找設計師全部都是自己來 所以有很多不懂之處 也問一大堆的問題 凱西小姐也非常不厭其煩地提醒我們要注意哪些事項 很符合我們的需求 完成品真的也超級贊 比我們之前想像的好很多 安裝工程師的實力很好 安裝後的垃圾 木屑也清理的很乾淨 整個品質真的沒有話說 有需求的朋友們真的可以找他們了解一下唷！

3.桃園南崁特力家居直營門市
A.W. ★★★★★
門市展示多種地板，還有樣板可以帶回去跟設計師討論。柳小姐介紹的很詳細，也能為客人設想幾種不同的搭配。最後決定選這間，施工的師傅非常專業又客氣。成品超有質感的，非常滿意。

王珮茹 ★★★★★
地板質感好、施工快速、符合預期。門市吳沛瀠小姐從洽談到完工，給予專業的建議及貼心的提醒，服務超棒

林姿吟 ★★★★★
從參觀吳小姐很細心～到丈量也都盡心盡力！連施工當天也到現場幫忙監工！有問題也都能得到相對回應！真的很謝謝這團隊！

4.新北中和HOLA直營門市
黃婷玉 ★★★★★
地板剛安裝完,業務陳耑瑜解說很詳細，有問題也很耐心說明有需求提出來討論也能提供專業建議施作團隊有4位師傅，工程比想像中快完成施工完成後覺得房子變得很有溫度。

dejeng dejeng (dejeng) ★★★★★
中和業務陳耑瑜服務一級棒，雖然我只安裝不到四坪，仍然優質，故推薦給大家。

鄧喬茵 ★★★★★
服務用心，說明專業，有耐心。地板美觀耐用，鋪設品質極佳，圓角部分處理，無可挑剔。

5.竹北HOLA直營門市
Guo-En Lin ★★★★★
門市邱先生很專業的介紹，建議的木板顏色很適合安裝空間。非常配合顧客的需求，安裝的師傅手法細膩，無論收邊或是施工後的環境清潔讓我們很滿意！大力推薦給還在尋找超耐磨木板的朋友們，一定不會失望！

吳青樺 ★★★★★
謝謝陳小姐在我們此次木地板工程中給予很完善的安排、很仔細的跟顧客提醒施作時的注意事項，遇上問題也能很迅速的協助處理；還有工班在施工時不論是在拆除跟鋪設都很細心。
真的是非常棒的團隊，讓我們有很舒適的成果。

Justin Wang ★★★★★
好評：品質,專業度
已經是我第二次回購 感謝彭小姐的細心解說和良好的服務品質,地板的選擇也很多,質感很不錯推薦給大家

6.台南仁德特力家居直營門市
Kyo Chen ★★★★★
來德國高能得思買木地板，下訂地板遇到劉小姐講解仔細服務好，來店購買要找劉小姐喔！ 

迷你世界:兔兔 ★★★★★
這次與貴公司購買地板從選購、安排日期、施工過程到結束都是一個愉快的經驗，謝謝林先生的接洽與服務，大力推薦！

馬妞 ★★★★★
好評： 值, 品質, 守時, 專業度, 積極回應
現場服務的劉小姐非常細心耐心的回答我們的問題，非常專業！甚至把木地板搬到隔壁的沙發區，讓我們比對新買的沙發顏色。整個購買流程非常的順暢，施工當天的年輕師傅們，非常專業以及施工品質都非常的好，施工結束後還把家具全部歸位，離開時也把環境打掃的非常乾淨！如果您有在找適合家裡的木地板，可以試試看他們家的專業服務與高品質哦！

7.高雄夢時代直營門市
Google Chen ★★★★★
好評： 值, 品質, 守時, 專業度, 積極回應
推周俞呈（周姐）的服務，耐心介紹產品，地板鋪後我跟內人都極度滿意成果

 
蔡榮杰 ★★★★★
好評： 品質, 專業度, 積極回應
業務服務人員態度親切，施工單位品質良好，如可搭配該公司活動價格優惠，推薦居家木質地板使用該公司產品。

Gary Chang ★★★★★
這是第二次選擇德國高能德思超耐磨地板，夢時代周小姐很專業推薦適合的產品，態度親切又專業的解說，這是選購白色宏觀木，施工完大人小孩都非常滿意，很推薦大家來購買!


8.高雄左營特力家居直營門市
林企茹 ★★★★★
去門市推薦蔡小姐，服務仔細而且有問題都認真回覆，看現場有疑問也是幫忙快速找師傅討論出解決方式

ao H ★★★★★
門市服務專員都非常專業，很有耐心的詳細介紹，非常推薦來這邊選購地板。

Alline Chen ★★★★★
感謝門市小姐的細心和施工師傅的用心，讓我們家的木地板可以順利修復，謝謝

【地板種類】
    德國高能得思地板有歐洲最新、最頂級、最酷的超耐磨木地板，包含12個系列，共有100多種花色，還有你沒看過的地板，可以仔細挑選。若需索取樣品，可以點選地板花色的愛心red heart，加入追蹤清單，可以選擇《門市取樣》或是《送樣到府》（1～5個型號花色）。
    強化木地板：由高密度纖維板製成，表面有耐磨層，外觀仿木紋，價格實惠、耐刮耐磨。
    SPC地板：石塑複合地板，具備100%完全防水、穩定不變形的特性，適合廚房或商業空間。
    工程木地板：表層真實木材，底層穩定結構，兼具質感與實用性。


【門市訊息】
1.台北內湖特力家居
    台北市內湖區新湖三路23號2F R

    特力家居 2樓

    TEL: 02-2796-2238

    FAX: 02-2796-2722

    營業時間:10:00~22:00 (全年無休)

    公車大眾運輸:下車站牌名稱－路線名稱，新湖三路口 聯營公車－ 204、518、藍7、小2、棕1

    停車停車資訊:新湖三路23號地上3、4樓

2.台北內湖設計建材中心
    台北市內湖區新湖一路185號3F306室 地圖

    設計建材中心 3樓306室

    TEL: 02-8791-1752

    FAX: 02-8792-8745

    營業時間:10:30~19:30

    公車大眾運輸:公車路線:204、518、63、207、藍 7、552、 950、藍 50、綠 16、小 2，至「新湖一路口」下車，步行 3 分鐘即可抵達。

    停車停車資訊:地下停車場

3.新莊紐約家具設計中心
    新北市新莊區思源路553號2樓 R

    紐約家具設計中心-新莊思源旗艦館 2樓

    TEL: 02-2246-3280、02-2246-1416

    FAX: 02-2246-2010

    營業時間:12:00~21:00 (全年無休)

    公車大眾運輸:1.搭乘捷運藍線從新埔站轉乘 : 搭乘918.813 至頭前國中(中原路)往思源路方向，直走步行600公尺即可到達本館。
                    2.從新北市捷運環狀線 : 轉機場捷運線A3新北產業園區站出口，往思源路方向直走步行750公尺即可到達本館。
                    3.搭乘機場捷運線 : 從A3新北產業園區站出口，往思源路方向直走步行750公尺即可抵達。

    停車停車資訊:新申辦會員無消費或會員無消費，可折抵1小時；會員無消費，有提供估價單或業代陪同，可折抵2小時；會員有消費最高可折抵3小時。

4.桃園南崁特力家居
    桃園市蘆竹區中正路1號B1-05建材館 R

    國道1號-南坎交流道旁 特力家居 地下1樓

    TEL: 03-212-0837

    FAX: 03-212-0805

    營業時間:11:00~22:00 (全年無休)

    公車大眾運輸:3路公車-菜公路口站(美術館站-警廣站).72路公車-菜公路口站(獅甲國小-金獅湖站) .91路公車-菜公路口站(大公路-金獅湖站)

    停車停車資訊:1F平面停車場、B1F地下停車場

5.竹北HOLA門市
    新竹縣竹北市光明六路89號3F R

    竹北HOLA 3樓

    TEL: 03-558-3018

    FAX: 03-558-3382

    營業時間:11:00~22:00 (全年無休)

    公車大眾運輸:新竹市區搭乘新竹客運往新埔或中壢方向車次，於竹北地政事務所下車 (步行約10分鐘)

    停車停車資訊:竹北HOLA停車4-7F

6.台南仁德特力家居
    台南市仁德區中山路777號B1F R

    特力家居 地下1樓

    TEL: 06-270-6335

    FAX: 06-270-8765

    營業時間:11:00~22:00 (全年無休)

    公車大眾運輸:紅幹線公車-仁德交流道站(安工區-關廟).紅2公車-仁德交流道站(台南-上崙子-關廟).8050路公車-仁德交流道站(台南-旗山-佛光山)

停車停車資訊: 1F平面停車場、B1F地下停車場

7.高雄左營特力家居
    高雄市左營區民族一路948之2號B1F R

    高雄左營 特力家居 地下1樓

    TEL: 07-347-5859

    FAX: 07-347-7955

    營業時間:11:00~22:00 (全年無休)

    大眾運輸:3路公車-菜公路口站(美術館站-警廣站).72路公車-菜公路口站(獅甲國小-金獅湖站).91路公車-菜公路口站(大公路-金獅湖站)

    停車資訊:1F平面停車場、B1F地下停車場

8.高雄夢時代門市
    高雄市前鎮區中華五路789號B2F R

    高雄夢時代 地下2樓 家居生活館內

    TEL: 07-823-2053、07-970-0768

    FAX: 07-970-1208

    營業時間:11:00~22:00 (全年無休)

    公車大眾運輸:1.15、36、70、214、中華幹線、168環狀東線/西線 請於夢時代站下車，即可抵達.2.25、69、12,3.168環狀東線/西線,4.168環狀東線/西線,5.請搭乘高雄捷運至R6(凱旋站)轉乘輕軌C3(前鎮之星站)至C5(夢時代站)下車

    停車停車資訊:中華五路789號地下B1~B5

【優惠活動】

    感恩母親節 活動時間：4/3～5/19

    全館地板88折起 (特價品除外)

    特價地板3480元起 (原價5980元/坪)

    門市簽單再享滿額折扣 (詳情請洽門市)

    滿10萬再送德國Brita濾水壺 (贈品不累贈)

【Q&A】
1.為什麼一定要有德國原廠的地板保固？

    木地板是室內裝修最重要的基本材料，是耐久商品，不是一般的消費品，可以用完即丟。它是安裝在地上，它是需要被長久使用，它是會關係到你家人健康的重要裝飾材料。
    特別是當你的裝修都已經完成，床，家俱都已經放在地板上面，如果你買到的是品質不好的地板，或是來路不明的平行輸入水貨地板，或是安裝技術不好的施工，若是地板損壞了，他們是不會幫你做維修，更不會有德國原廠的地板保固。劣質的仿冒地板甚至可能影響到你家人的健康，不可不慎！
    而且地板的維修和重新更換是會影響到正常的家居生活，也是一件很勞民傷財的事情，特別是若沒有德國原廠的地板保固，更是會雪上加霜。
    所以請即將購買地板的客戶，一定要在德國高能得思地板專賣店購買地板，才能得到德國原廠的地板保固，才能買的舒心，用的安心！

2.網路客戶訂購流程?
    訂購丈量施工流程：

    A.直接在官網點選立即估價：
    你可以在地板系列裏，選擇喜歡的地板型號，點選立即估價、或免費樣板、或免費丈量、或免費目録，公司將安排專人為您服務、估價、丈量。 

    B.直接打電話:
    告知設計銷售顧問是網路客人，詢問價格及優惠活動，並寄送樣品，確定顏色型號。

    C.或親臨門市:
    至門市告知是網路客人，詢問價格及優惠活動，確定顔色型號，完成訂購

    D.免費安排丈量:
    確定施工現場情形及施工方式（地坪是否平整及大約坪數）

    E.繳付訂單:
    設計銷售顧問幫客戶填寫訂單，客戶繳付3成訂金（因是原裝進口地板，需保留地板-如遇斷貨需等4個半月），確定客戶喜歡的地板型號及地板坪數

    F.告知施工日期:
    10日前客戶電話告知要施工日期，安排施工，付清餘款。

    G.地板施工:
    施工當日，地板送到施工現場，客戶確認型號及數量後完成簽收，現場馬上安裝地板（15坪內  一天即可完成）地板完工後，客戶現場驗收。

    H.多退少補（最小單位為包）未拆封完整地板可退款: 
    客戶施工驗收完成後，多退少補(最小單位為包)，結清餘款。

3.為何一定要在kronotex高能得思的專賣店購買地板？
    只有在kronotex許可的專賣店購買，才能得到德國原廠的25～30年品質保固
    只有是kronotex培訓過的工班團隊施工，才能得到一年的施工保固
    產品從德國工廠直接到高能得思專賣店，沒有任何其他的中間環節，客戶可以用近乎很便宜的團購價格，來購買德國頂級木地板，物超所值。
    地板的品質和地板的施工，不同於一般的家電用品或衣服，不是丟掉或不用就好，來源不明或是品質不好的地板，可能會影響正常的家居生活和您家人的健康。
    遇到施工不良的廠商或工班，或是來路不明的平行輸入水貨商品，他們沒有德國原廠的保固，也沒有施工的產品保固書，當地板有問題需要維修或整個地板品質不良需要拆除，他們都不會理你。維修地板也要搬動家俱，更會影響到您正常的家居生活。
    所以買地板前一定要謹慎考慮。有著良好品牌和優秀施工團隊的kronotex德國高能得思地板才是您最佳首選的地板，因為地板是要使用20～30年以上。

4.高能得思Kronotex地板在國內有那些不同厚度產品？
    從德國進口入台灣市場的高能思Kronotex地板，在厚度上有8mm、10mm和12mm三種厚度，分屬五種系列
    動感系列 厚度為8mm
    精緻系列 厚度為8mm
    亞瑪遜系列 厚度為10mm
    活力系列 厚度為12mm
    瑪木特系列 厚度為12mm
    瑪木特plus系列 厚度為10mm
    時尚系列       厚度為8mm
    人字拼系列    厚度為8mm
    水奇異系列    厚度為5.5mm

6.高能得思地板為什麼最受歡迎？
    高能得思地板是德國Kronotex原廠生產的超耐磨地板，因為地板花號最漂亮，有著全球首創100%防水木地板，業界技術創新領先。地板從德國工廠直送專賣店，沒有中間環節，讓您在台灣也能享受到來自德國的木地板。凡舉實木地板表面能顯示的真實感優點都包含，且有以下的特點：防潑水，頂級防潮基材，容易維護、耐久性佳、具防焰性、耐煙灼性、色澤特久、耐光性佳、耐污性佳、耐磨性特強、符合歐洲環保E1標準、抗靜電性佳、行走具舒適性、耐荷重、抗衝擊性佳，且適用於地熱系統表面等特色優點。

7. 目前市面上常見的地板有那些類別？
    目前市面上常見的地板大致上可歸屬實木地板、海島型地板及超耐磨地板三大類
    實木地板－材料：實木+表面噴漆塗裝(以UV為大宗)。
    海島型地板－材料：(1)實木面材+表面噴漆塗裝+夾板層(2)美耐板材+夾板層。
    超耐磨地板－材料：高密度木纖維複合板+超耐磨Al2O3表面塗層。
 
8. 德國高能得思地板保固期保固內容如何？
    為了使客戶有更完善的服務，我們提供一年的施工保固，確保客戶使用地板一年內，如有施工不良或材料品質的問題，可以得到我們地板施工保固的確認。

9. 如要加舖高能思地板，會破壞到原有的石材地面嗎？
    高能得思地板的標準舖法是漂浮施工法的直舖工法，在原有的地面上舖上一層2mm的防潮層後即可直接舖上高能得思地板，且施工時不須打釘子，所以不會破壞到原有的石材，且原廠對居家長達25～30年的耐用保固，也方便拆除，可移到別處重複施工使用。選用高能得思地板實是最佳的選擇。
 
11. 高能得思地板用何種配件收邊？
    高能得思地板能提供的收邊配件相當多樣，如踢腳板、L型收邊條、一字收邊條、起步條、分隔條、小圓弧收邊條、樓收條或矽利康收邊等可因應不同環境需要。

13. 高能得思的TPE防水隔音墊(3.0mm)有那些優點？
    高能得思的TPE防水隔音墊能結合抗壓性和彈性，舖設於複合地板之下隔阻噪音非常有效，其功能優點如下：
    可將高音頻率轉換為較低頻率的聲音，大大增加房間的寧靜與舒適度。
    TPE防水隔音墊也可隔絕大部份的衝擊音，如此可大大的降低噪音傳播到樓下樓層。
    可使區域不平地面的地板變平穩，增加地板的穩定性。
 

14. 如何知道（證明）德國高能得思地板是最穩定又最能防潑水抗潮濕的地板？

    眾所皆知，吸水厚度膨脹率是地板關鍵性的檢驗指標之一。它代表著地板本身的穩定性和防潑水抗潮濕的能耐。尤其在海島型潮濕氣候的台灣更是重要。依CNS11342的檢測規範中，試片在（25+-1）0C浸漬24小時後，測其相同位置之厚度，由下式計算出吸水厚度膨脹率：

    吸水厚度膨脹率％＝t2-t1／t1X100

    t1：吸水前之厚度（mm）
    t2：吸水後之厚度（mm）
    我國標檢局檢測的合格標準如下：

    試片厚度≧12.7mm者，其吸水厚度膨脹率≦20%為合格。
    試片厚度＜12.7mm者，其吸水厚度膨脹率≦25%為合格。
    高能得思地板由標檢局依CNS11342實測得吸水厚度膨脹率如下：
    AC5（12mm）：吸水厚度膨脹率為0.1%
    AC4（ 8mm）：吸水厚度膨脹率為0.11%
    由標檢局實際測試報告得知的數據即可深信德國高能得思地板是既穩定又防潑水抗潮濕的地板。(參考某K牌頂級地板的吸水厚度膨脹率為7.84%)

    防潑水木地板，頂級防潮基材

15. 德國原裝進口的高能得思地板價格會很貴嗎？
    身為全球最大木地板製造商Kronotex德國原廠的生產系列廣泛。高能得思地板在台灣出售的產品，則分佈於厚度8mm AC4等級到厚度12mm AC5的頂級產品，而每坪訂價從＄3,680起（含施工費），而且原廠對產品的家居正常使用保固期長達25～30年。依德國高水準的生產工藝價值，就如有人比喻「用國產車的價格就能享受到德國雙B名車的價值」，真是物超所值，公司也會不定期針對一些產品做特價活動。客戶能以優惠的價格買到德國高品質的地板，歡迎來電0800-558708或親臨展廳洽詢。

16. 我在宜蘭市，你們展示廳（專賣店）在宜蘭沒有設立，你們也可以施工嗎？
    可以。德國高能得思地板的專業施工人員可以在全台施工，我們的設計銷售顧問可以幫您們寄送樣品、選樣品及安排施工，我們的客戶包含全台各縣市，甚至澎湖、金門地區都有，您可以放心選購我們的產品。
 

17. 你們地板可以用在商業空間嗎？例如餐廳或展示廳
    可以。我們進口到台灣的地板每個系列都適用於商業空間，因為高能得思地板是超耐磨地板，耐磨轉數等級屬於商用AC4及AC5，適用於商場、辦公室、賓館，甚至人潮眾多的百貨公司。現在新裝修的德國福斯汽車展示廳，都是選用我們的地板「精緻系列－巧克力木（型號：D2236MO）」，即使很重的車子壓在我們地板上，也沒關係，並不會產生壓痕。
 

18. 為什麼許多設計師都喜歡用高能得思地板？
    因為德國高能得思地板每隔3個月～6個月都會有新的顏色和型號進口到台灣，基本上都是跟歐洲同步。我們的顏色和型號也是業內最多的（多達80餘種），一般設計師對顏色是最敏銳的，我們的地板產品品質、顏色和服務都能滿足設計師的要求，所以您在很多設計師的案場（例如遠雄左岸樣品屋）都可以看到高能得思地板。
 

19. 可以只買地板，自己安裝嗎？可以扣多少工資？
    當然可以。在歐洲、美國因為工資較高，所以很多客戶都選擇自行安裝，因為我們地板都是使用最先進「快速鎖扣系統（Express Clic System）」，安裝簡易、安全又穩固，只要您有施工的工具，參考我們的地板技術，我們的銷售顧問也會跟您解說施工時應注意事項。若您自行施工，安裝工資可以減900元/坪，我們地板可以配送到施工現場。

20. 為何最多豪宅建案喜歡採用Kronotex高能得思地板？
    一般建商採購建材商品會考慮到（1）顧客的接受性（2）品牌的知名度（3）品質的穩定性（4）建材的價值比及施工的難易性。
    高能得思地板是從德國原裝進口的全球第一大品牌，品質的穩定性及品牌的知名度皆深得國人的信賴，顧客的接受度高。採用不需打釘的直舖法，施工容易，且又有物超所值的價值比等因素，皆能迎合建商的考量及喜好，故有許多建案室內地板的採購選擇Kronotex高能得思超耐磨地板。

21. 請問你們各個系列，價格差那麼多，是差在哪裡？
    基本上地板價格會因耐磨系數、厚度、有無倒角及表面處理之不同而有所差別。
    差在耐磨系數，耐磨系數越高越貴（AC5>AC4）
    差在厚度，厚度越厚越貴（12mm>10mm>8mm）
    差在倒角，同厚度相比（有倒角>無倒角）
    差在表面紋路處理，同厚度相比或同系列相比（表面有鍍鉻較貴）
    差在長度，同厚度相比（長度較長較貴）
    

22. 德國高能得思地板為何要設立品牌專賣店？
    為了讓客戶能了解品牌的重要性，德國的工藝、歐洲現在流行的趨勢顏色，這些都需要有專賣店。
    我們不像仿間一般建材公司，什麼地板都賣，我們只專賣德國高能得思地板，客戶能看到地板大面積的鋪設效果，在店裡也能得到公司設計銷售顧問專業親切的服務與解說。

23. 在專賣店裡，我能看到什麼？
    德國高能得思地板專賣店是目前在台灣最專業的地板展示廳。店裡有各系列80餘種花色，有許多最新、最酷的地板花色，您沒看過的地板，您都可以在專賣店裡找到。

25.什麼是高能得思的三大承諾保證？
    【高能得思的三大承諾保證】
    a.Recyclable:地板產品可以被回收,
    在地板產品的最後生命過期,我們的地板是可以被回收,而且是
    可以當成完全不含有害物質的廢棄物。
    b.PVC-Free:高能得思地板完全不含PVC和塑化劑。
    c.Sustainable Forestry:可持續發展的森林策略,
    Kronotex的木材源自德國布蘭登堡 FSC認證區的環保永續森
    林:永績森林是有計劃性的植栽、養護及砍伐的森林,讓森林資
    源可以永續不問斷的發展·Kronotex為全球唯一木芯基材採用布蘭登堡原樹林區製造

"""


floor_data = [
    {"model": "D3597 TIMELESS OAK BEIGE 永恆貝格橡木", "color": "淺木色", "waterproof": False, "原價": 7880, "價格": 5880, "thickness": 10},
    {"model": "KIWI 40522 Opal Oak Coffee 歐柏咖啡橡木", "color": "深木色", "waterproof": True, "原價": 7180, "價格": 5080, "thickness": 5.5},
    {"model": "Oriental Oak White 東方白橡木", "color": "灰色", "waterproof": False, "原價": 6680, "價格": 4880, "thickness": 8}
]

floor_image_map = {
    "KIWI 40522 Opal Oak Coffee": ["https://www.kronotex.com.tw/USER/Userfile/file/ff230710145014289511.jpg","https://www.kronotex.com.tw/USER/Userfile/file/ff240103155308113648.jpg","https://www.kronotex.com.tw/USER/Userfile/file/ff240628141957742183.jpg"],
    "D3597 TIMELESS OAK BEIGE": ["https://www.kronotex.com.tw/USER/Userfile/file/ff230710145014289511.jpg","https://www.kronotex.com.tw/USER/Userfile/file/ff240729140026590460_l.jpg?t=1722232826970","https://www.kronotex.com.tw/USER/Userfile/file/ff220830210308016703.jpg"],
    "Oriental Oak White": ["https://www.kronotex.com.tw/USER/Userfile/file/ff230710144554174555.jpg","https://www.kronotex.com.tw/USER/Userfile/file/ff240806140923824105.jpg?t=1722924579708","https://www.kronotex.com.tw/USER/Userfile/file/ff230427172054959370.jpg"],
}
# ======== 3. Webhook 接收區 ========
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@app.route("/", methods=["GET"])
def index():
    return "FloorBot is running!", 200

def format_floor_data(data):
    result = "以下是目前可供選擇的地板資訊：\n"
    for item in data:
        result += (
            f"【{item['model']}】\n"
            f"- 顏色：{item['color']}\n"
            f"- 厚度：{item['thickness']}mm\n"
            f"- 是否防水：{'是' if item['waterproof'] else '否'}\n"
            f"- 原價：{item['原價']} 元\n"
            f"- 特價：{item['價格']} 元\n\n"
        )
    return result

# ======== 4. 訊息處理區 ========
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_msg = event.message.text
    timestamp = datetime.now().isoformat()
    conn = psycopg2.connect(**DB_PARAMS)
    c = conn.cursor()

    img_keywords = ["圖片", "照片", "看看", "圖", "photo", "picture", "image"]

    if any(keyword in user_msg.lower() for keyword in img_keywords):
        # 是圖片需求，不送給 ChatGPT，而由你處理
        matched_model = None
        for model_name in floor_image_map:
            if model_name.lower() in user_msg.lower():
                matched_model = model_name
                break


        if matched_model:
            # 找到對應型號 → 傳圖片
            images = [
                ImageSendMessage(
                    original_content_url=url,
                    preview_image_url=url
                )
                for url in floor_image_map[matched_model][:3]
            ]
            image_response_message = f"這是「{matched_model}」的圖片："
            messages = [TextSendMessage(text=image_response_message)] + images
        else:
            # 沒找到地板型號 → 給個通用提示
            image_response_message = "請告訴我您想看的地板型號，我就能提供圖片！我們目前支持三種型號：D3597 TIMELESS OAK BEIGE 永恆貝格橡木， KIWI 40522 Opal Oak Coffee 歐柏咖啡橡木 或是 Oriental Oak White 東方白橡木"
            messages = [TextSendMessage(text=image_response_message)]

        # 最多回傳 5 則（LINE 限制）
        messages = messages[:5]
        line_bot_api.reply_message(event.reply_token, messages)
        c.execute("""
            INSERT INTO chat_logs (timestamp, user_id, user_message, bot_reply)
            VALUES (%s, %s, %s, %s)
        """, (timestamp, user_id, user_msg, image_response_message))
        conn.commit()
        conn.close()

        return  # 結束這次處理，不再進入 ChatGPT API


    # 客戶要求真人服務的關鍵字
    keywords = ["真人", "專人", "銷售", "找人", "聯絡人", "打電話", "真人客服"]
    if any(keyword in user_msg for keyword in keywords):
        agent_message = "好的，我們會通知銷售專員，請稍等～"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=agent_message)
        )
        c.execute("""
            INSERT INTO chat_logs (timestamp, user_id, user_message, bot_reply)
            VALUES (%s, %s, %s, %s)
        """, (timestamp, user_id, user_msg, agent_message))
        conn.commit()
        conn.close()

        return  # 結束這次處理，不再進入 ChatGPT API


    c.execute("""
        SELECT user_message, bot_reply FROM chat_logs
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 5
    """, (user_id,))
    recent_conversations = c.fetchall()
    chat_history = []
    for msg, reply in reversed(recent_conversations):
        chat_history.append({"role": "user", "content": msg})
        chat_history.append({"role": "assistant", "content": reply})


    # def filter_floors(user_input):
    #     result = []

    #     if "防水" in user_input:
    #         result = [f for f in floor_data if f["waterproof"]]

    #     # 可以加更多條件（厚度、顏色、預算）
    #     return result

    # filtered_floors = filter_floors(user_msg)

    # if filtered_floors:
    #     product_text = "\n".join([
    #         f'{f["model"]} / 顏色：{f["color"]} / 價格：{f["價格"]}元 / 厚度：{f["thickness"]}mm / 防水：{"是" if f["waterproof"] else "否"}'
    #         for f in filtered_floors
    #     ])
    # else:
    #     product_text = "目前找不到符合條件的地板。"

    # 呼叫 OpenAI ChatGPT 來分析需求並推薦地板

    formatted_floor_info = format_floor_data(floor_data)

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": (
                "你是一位地板顧問，會根據使用者輸入進行公司介紹、地板知識說明"
                f"\n以下是你可參考的知識內容：\n\n{knowledge_text}， 並且根據下列資料推薦適合的地板：{formatted_floor_info}"
            )}
        ] + chat_history + [{"role": "user", "content": user_msg}],
        temperature=0.7
    )

    bot_reply = response.choices[0].message.content

    c.execute("""
        INSERT INTO chat_logs (timestamp, user_id, user_message, bot_reply)
        VALUES (%s, %s, %s, %s)
    """, (timestamp, user_id, user_msg, bot_reply))
    conn.commit()
    conn.close()

    messages = [TextSendMessage(text=bot_reply)]
    for model_name, image_list in floor_image_map.items():
        if model_name in bot_reply:
            for img_url in image_list:
                messages.append(ImageSendMessage(
                    original_content_url=img_url,
                    preview_image_url=img_url
                ))
    # 最多回傳 5 則（LINE 限制）
    messages = messages[:5]

    line_bot_api.reply_message(event.reply_token, messages)

if __name__ == "__main__":
    app.run(port=5000)
