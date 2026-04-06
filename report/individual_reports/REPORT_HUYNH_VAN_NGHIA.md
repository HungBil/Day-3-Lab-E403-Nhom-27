# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Huynh Van Nghia
- **Student ID**: 2A202600085
- **Date**: 06/04/2026

---

## I. Technical Contribution (15 Points)

Em tập trung xây dựng trải nghiệm frontend cho bài toán Travel Planner để người dùng có thể truy cập và tương tác với quy trình agent một cách rõ ràng.

- **Modules Implementated**:
  - services/frontend/index.html
  - services/frontend/chat.html
  - services/frontend/styles.css

- **Code Highlights**:
  - Triển khai điều hướng từ trang landing sang trang chat thông qua nút Start Planning.
  - Xây dựng trang giao diện chat riêng cho Travel Planner Agent, gồm bong bóng chat, ô nhập tin nhắn và các gợi ý prompt mẫu.
  - Bổ sung responsive layout cho desktop và mobile với các breakpoint phù hợp.
  - Cải thiện khả năng truy cập và tính dễ dùng với skip-to-content, trạng thái nav đang active, focus-visible và hỗ trợ reduced motion.
  - Tăng tính đồng bộ giao diện bằng hệ thống design token, nền gradient và các style button/card có thể tái sử dụng.

- **Documentation**:
  - Frontend cung cấp lớp giao diện rõ ràng để hiển thị và so sánh giữa vòng lặp ReAct và chatbot baseline.
  - Trang landing hướng người dùng vào luồng chat, trong khi trang chat được tổ chức để hiển thị phản hồi theo kiểu Thought-Action-Observation dạng hội thoại.
  - Bản hiện tại sử dụng HTML và CSS tĩnh; bước tích hợp tiếp theo là kết nối ô nhập với endpoint backend gọi Chatbot Baseline và ReAct Agent.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**:
  - Ở trang chat, khi bấm Send thì form submit mặc định làm trang bị refresh và làm mất tính liên tục của hội thoại.

- **Log Source**:
  - Kiểm tra thủ công trên trình duyệt trong quá trình frontend QA tại services/frontend/chat.html.

- **Diagnosis**:
  - Form dùng method get và nút Send để type submit, vì vậy mỗi lần bấm đều kích hoạt điều hướng/reload trang.
  - Hành vi này không phù hợp với UX chat agent, nơi lịch sử tin nhắn cần được giữ nguyên để theo dõi ngữ cảnh.

- **Solution**:
  - Chuyển nút Send sang type button để tránh reload ngoài ý muốn trong giai đoạn UI tĩnh.
  - Bổ sung nhóm gợi ý chat và cải tiến bố cục khu vực tin nhắn để giữ ngữ cảnh hiển thị tốt hơn.
  - Làm rõ cấp bậc trang và chỉ dẫn điều hướng (nav active, subtitle, focus handling) để giảm lỗi thao tác.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**:
  - Kiểu tương tác ReAct phù hợp hơn với bài toán lập kế hoạch du lịch nhiều bước vì có thể thu thập dữ liệu theo từng giai đoạn (thông tin điểm đến, ước tính chi phí, kiểm tra ngân sách) trước khi đưa ra câu trả lời cuối.
  - Chatbot trả lời trực tiếp có thể trôi chảy về câu chữ nhưng dễ bỏ qua các bước tính toán minh bạch.

2. **Reliability**:
  - Với các câu hỏi một lượt đơn giản (ví dụ chỉ hỏi thời tiết), chatbot trực tiếp có thể cho cảm giác nhanh hơn do không phải qua nhiều bước suy luận/gọi tool.
  - ReAct có thể chậm hơn trong các trường hợp này vì cần thêm các bước lập kế hoạch.

3. **Observation**:
  - Observation là tín hiệu điều khiển quan trọng nhất đối với agent.
  - Mỗi kết quả tool đều ràng buộc hành động tiếp theo, tăng khả năng truy vết và giúp câu trả lời cuối bám sát dữ liệu đã truy xuất thay vì đoán.

---

## IV. Future Improvements (5 Points)

- **Scalability**:
  - Bổ sung cơ chế chat thời gian thực (streaming bằng SSE hoặc WebSocket) và quản lý session theo từng người dùng.

- **Safety**:
  - Thêm xác thực đầu vào và guardrail cho phản hồi ở backend API trước khi hiển thị lên giao diện chat.

- **Performance**:
  - Bổ sung cơ chế cache nhẹ ở phía client cho các truy vấn du lịch lặp lại và hiển thị tóm tắt latency/tokens theo mỗi phản hồi để phục vụ so sánh thí nghiệm.

---

> NOTE
> Submit this report by renaming it to REPORT_[YOUR_NAME].md and placing it in this folder.
