# Quy tắc an toàn khi làm việc với repository

- Không được tự ý tạo commit. Chỉ commit khi người dùng yêu cầu rõ ràng trong cuộc trò chuyện hiện tại.
- Không được tự ý push, force-push, tạo pull request, merge hoặc rebase. Phải có yêu cầu rõ ràng của người dùng cho đúng hành động và đúng branch.
- Nhánh `main` là nhánh được bảo vệ: tuyệt đối không tự ý commit trên `main`, push lên `main`, hoặc tạo pull request nhắm vào `main`. Chỉ được thực hiện từng hành động khi người dùng cho phép rõ ràng trong cuộc trò chuyện hiện tại.
- Không được tự ý xóa file, thư mục, branch, tag, commit hoặc lịch sử Git. Nếu việc xóa là cần thiết nhưng chưa được yêu cầu rõ ràng, phải hỏi người dùng trước.
- Mọi thao tác xóa, ghi đè, làm rỗng, thay thế hoặc migration có khả năng gây mất mát đối với tài sản quan trọng — bao gồm database, bảng hoặc dữ liệu; dataset; model, checkpoint hoặc trọng số; thuật toán cốt lõi; và mã nguồn quan trọng — đều phải có sự cho phép rõ ràng của người dùng trước khi thực hiện. Sự cho phép phải nêu đúng đối tượng và hành động; không được suy diễn từ một yêu cầu chung chung.
- Tuyệt đối không chạy các lệnh có khả năng làm mất dữ liệu như `git reset --hard`, `git clean`, `git checkout --`, `git restore` để hủy thay đổi, `git push --force`, hoặc lệnh tương đương nếu chưa có sự chấp thuận rõ ràng của người dùng.
- Trước mọi commit hoặc push đã được cho phép, phải kiểm tra `git status` và `git diff`, bảo đảm chỉ bao gồm đúng các thay đổi thuộc phạm vi yêu cầu.
- Không stage các file ngoài phạm vi công việc. Không sửa, ghi đè hoặc hoàn tác thay đổi sẵn có của người dùng.
- Khi yêu cầu có thể được hiểu theo nhiều cách, ưu tiên hành động không phá hủy và hỏi lại trước khi thực hiện thao tác khó khôi phục.
