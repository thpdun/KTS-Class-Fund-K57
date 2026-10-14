## Lần 1: Rà soát Quy tắc Kinh tế (Lab 8)
**Prompt:** Bạn là người dùng thận trọng. Chỉ dựa trên SPEC và ECONOMIC_RULES dưới đây, hãy nêu 5 cách một người có thể lạm dụng quy tắc...
**AI trả về:** Trình bày 5 lỗ hổng nghiêm trọng gồm: Lợi dụng 7 ngày để rút tiền, Thao túng tỷ lệ 51% bằng quyền CVHT, Tiền hoàn bị kẹt do thiếu phí gas, Tạo nhiều lệnh rút cạn quỹ, và Spam hoàn tiền 1 wei.
**Đánh giá:** AI phân tích chính xác. Các lỗ hổng logic này hoàn toàn có thể xảy ra trong thực tế.
**Cách sửa:**
- Nhóm đã sửa lại quy tắc R2, R5 và bổ sung R8 vào tệp SPEC.md để bít lỗ hổng 7 ngày, chặn tạo nhiều lệnh cùng lúc và chặn spam 1 wei.
- Nhóm quyết định chấp nhận rủi ro lạm quyền của CVHT và rủi ro đùn đẩy phí gas, ghi chú rõ ràng vào Mục 4 của tệp ECONOMIC_RULES.md vì việc sửa code sẽ làm dự án v0.1 quá phức tạp.
**Ai phát hiện:** Công cụ AI.