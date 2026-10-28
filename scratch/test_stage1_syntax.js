
    // --- 1. CONFIGURATION ---
    const CONFIG = {
      chainId: 11155111,
      chainIdHex: "0xaa36a7",
      chainName: "Ethereum Sepolia Testnet",
      blockExplorer: "https://sepolia.etherscan.io",
      defaultContractAddress: "0xe3e1db1da1cae10e92337c36bb13004bf984ee91",
      contractAddress: "0xfe3ec1a75503Da9ddFd44aEBE18E461686376b52"
    };

    // Full ProjectCore ABI
    const CONTRACT_ABI = [{ "inputs": [], "stateMutability": "nonpayable", "type": "constructor" }, { "inputs": [{ "internalType": "uint256", "name": "requestId", "type": "uint256" }, { "internalType": "address", "name": "voter", "type": "address" }], "name": "AlreadyVoted", "type": "error" }, { "inputs": [{ "internalType": "uint256", "name": "refundId", "type": "uint256" }, { "internalType": "address", "name": "voter", "type": "address" }], "name": "AlreadyVotedRefund", "type": "error" }, { "inputs": [], "name": "ETHTransferFailed", "type": "error" }, { "inputs": [{ "internalType": "uint256", "name": "requested", "type": "uint256" }, { "internalType": "uint256", "name": "available", "type": "uint256" }], "name": "InsufficientAdminFee", "type": "error" }, { "inputs": [{ "internalType": "uint256", "name": "requested", "type": "uint256" }, { "internalType": "uint256", "name": "available", "type": "uint256" }], "name": "InsufficientAvailableFund", "type": "error" }, { "inputs": [{ "internalType": "uint256", "name": "requested", "type": "uint256" }, { "internalType": "uint256", "name": "available", "type": "uint256" }], "name": "InsufficientContribution", "type": "error" }, { "inputs": [{ "internalType": "uint256", "name": "requested", "type": "uint256" }, { "internalType": "uint256", "name": "available", "type": "uint256" }], "name": "InsufficientFund", "type": "error" }, { "inputs": [], "name": "InvalidAddress", "type": "error" }, { "inputs": [{ "internalType": "uint256", "name": "refundId", "type": "uint256" }], "name": "InvalidRefundStatus", "type": "error" }, { "inputs": [{ "internalType": "uint256", "name": "requestId", "type": "uint256" }], "name": "InvalidRequestStatus", "type": "error" }, { "inputs": [], "name": "NoActiveBCS", "type": "error" }, { "inputs": [], "name": "NotActiveBCS", "type": "error" }, { "inputs": [], "name": "NotAdvisor", "type": "error" }, { "inputs": [{ "internalType": "uint256", "name": "refundId", "type": "uint256" }], "name": "RefundAlreadyExecuted", "type": "error" }, { "inputs": [{ "internalType": "uint256", "name": "refundId", "type": "uint256" }], "name": "RefundExpired", "type": "error" }, { "inputs": [{ "internalType": "uint256", "name": "refundId", "type": "uint256" }], "name": "RefundRequestNotFound", "type": "error" }, { "inputs": [{ "internalType": "uint256", "name": "refundId", "type": "uint256" }], "name": "RefundVotingPeriodEnded", "type": "error" }, { "inputs": [{ "internalType": "uint256", "name": "refundId", "type": "uint256" }], "name": "RefundVotingStillActive", "type": "error" }, { "inputs": [{ "internalType": "uint256", "name": "requestId", "type": "uint256" }], "name": "RequestAlreadyExecuted", "type": "error" }, { "inputs": [{ "internalType": "uint256", "name": "requestId", "type": "uint256" }], "name": "RequestExpired", "type": "error" }, { "inputs": [{ "internalType": "uint256", "name": "requestId", "type": "uint256" }], "name": "RequestNotFound", "type": "error" }, { "inputs": [{ "internalType": "uint256", "name": "yesVotes", "type": "uint256" }, { "internalType": "uint256", "name": "activeBCSCount", "type": "uint256" }], "name": "ThresholdNotMet", "type": "error" }, { "inputs": [{ "internalType": "uint256", "name": "requestId", "type": "uint256" }], "name": "VotingPeriodEnded", "type": "error" }, { "inputs": [{ "internalType": "uint256", "name": "requestId", "type": "uint256" }], "name": "VotingStillActive", "type": "error" }, { "inputs": [], "name": "ZeroAmount", "type": "error" }, { "anonymous": false, "inputs": [{ "indexed": true, "internalType": "address", "name": "student", "type": "address" }, { "indexed": false, "internalType": "uint256", "name": "feeAmount", "type": "uint256" }], "name": "AdminFeeCollected", "type": "event" }, { "anonymous": false, "inputs": [{ "indexed": true, "internalType": "address", "name": "advisor", "type": "address" }, { "indexed": false, "internalType": "uint256", "name": "amount", "type": "uint256" }], "name": "AdminFeeWithdrawn", "type": "event" }, { "anonymous": false, "inputs": [{ "indexed": true, "internalType": "address", "name": "member", "type": "address" }, { "indexed": false, "internalType": "bool", "name": "status", "type": "bool" }], "name": "BCSMemberUpdated", "type": "event" }, { "anonymous": false, "inputs": [{ "indexed": true, "internalType": "address", "name": "student", "type": "address" }, { "indexed": false, "internalType": "uint256", "name": "amount", "type": "uint256" }], "name": "FundDeposited", "type": "event" }, { "anonymous": false, "inputs": [{ "indexed": true, "internalType": "address", "name": "student", "type": "address" }, { "indexed": false, "internalType": "uint256", "name": "amount", "type": "uint256" }], "name": "RefundProcessed", "type": "event" }, { "anonymous": false, "inputs": [{ "indexed": true, "internalType": "uint256", "name": "refundId", "type": "uint256" }, { "indexed": true, "internalType": "address", "name": "applicant", "type": "address" }, { "indexed": false, "internalType": "uint256", "name": "amount", "type": "uint256" }, { "indexed": false, "internalType": "string", "name": "reason", "type": "string" }, { "indexed": false, "internalType": "uint256", "name": "createdAt", "type": "uint256" }], "name": "RefundRequestCreated", "type": "event" }, { "anonymous": false, "inputs": [{ "indexed": true, "internalType": "uint256", "name": "refundId", "type": "uint256" }, { "indexed": true, "internalType": "address", "name": "applicant", "type": "address" }, { "indexed": false, "internalType": "uint256", "name": "amount", "type": "uint256" }], "name": "RefundRequestExecuted", "type": "event" }, { "anonymous": false, "inputs": [{ "indexed": true, "internalType": "uint256", "name": "refundId", "type": "uint256" }], "name": "RefundRequestExpired", "type": "event" }, { "anonymous": false, "inputs": [{ "indexed": true, "internalType": "uint256", "name": "refundId", "type": "uint256" }], "name": "RefundRequestReady", "type": "event" }, { "anonymous": false, "inputs": [{ "indexed": true, "internalType": "uint256", "name": "refundId", "type": "uint256" }, { "indexed": true, "internalType": "address", "name": "voter", "type": "address" }, { "indexed": false, "internalType": "bool", "name": "support", "type": "bool" }, { "indexed": false, "internalType": "uint256", "name": "yesVotes", "type": "uint256" }, { "indexed": false, "internalType": "uint256", "name": "noVotes", "type": "uint256" }], "name": "RefundRequestVoted", "type": "event" }, { "anonymous": false, "inputs": [{ "indexed": true, "internalType": "uint256", "name": "requestId", "type": "uint256" }, { "indexed": true, "internalType": "address", "name": "creator", "type": "address" }, { "indexed": true, "internalType": "address", "name": "recipient", "type": "address" }, { "indexed": false, "internalType": "uint256", "name": "amount", "type": "uint256" }, { "indexed": false, "internalType": "string", "name": "description", "type": "string" }, { "indexed": false, "internalType": "uint256", "name": "createdAt", "type": "uint256" }], "name": "SpendRequestCreated", "type": "event" }, { "anonymous": false, "inputs": [{ "indexed": true, "internalType": "uint256", "name": "requestId", "type": "uint256" }, { "indexed": true, "internalType": "address", "name": "recipient", "type": "address" }, { "indexed": false, "internalType": "uint256", "name": "amount", "type": "uint256" }], "name": "SpendRequestExecuted", "type": "event" }, { "anonymous": false, "inputs": [{ "indexed": true, "internalType": "uint256", "name": "requestId", "type": "uint256" }], "name": "SpendRequestExpired", "type": "event" }, { "anonymous": false, "inputs": [{ "indexed": true, "internalType": "uint256", "name": "requestId", "type": "uint256" }], "name": "SpendRequestReady", "type": "event" }, { "anonymous": false, "inputs": [{ "indexed": true, "internalType": "uint256", "name": "requestId", "type": "uint256" }, { "indexed": true, "internalType": "address", "name": "voter", "type": "address" }, { "indexed": false, "internalType": "bool", "name": "support", "type": "bool" }, { "indexed": false, "internalType": "uint256", "name": "yesVotes", "type": "uint256" }, { "indexed": false, "internalType": "uint256", "name": "noVotes", "type": "uint256" }], "name": "SpendRequestVoted", "type": "event" }, { "inputs": [], "name": "BPS_DENOMINATOR", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" }, { "inputs": [], "name": "FEE_BPS", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" }, { "inputs": [], "name": "PASSING_THRESHOLD_BPS", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" }, { "inputs": [], "name": "VOTING_PERIOD", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" }, { "inputs": [], "name": "activeBCSCount", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" }, { "inputs": [], "name": "adminFeePool", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" }, { "inputs": [], "name": "advisor", "outputs": [{ "internalType": "address", "name": "", "type": "address" }], "stateMutability": "view", "type": "function" }, { "inputs": [], "name": "classFundBalance", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" }, { "inputs": [{ "internalType": "uint256", "name": "amount", "type": "uint256" }, { "internalType": "string", "name": "reason", "type": "string" }], "name": "createRefundRequest", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "nonpayable", "type": "function" }, { "inputs": [{ "internalType": "address payable", "name": "recipient", "type": "address" }, { "internalType": "uint256", "name": "amount", "type": "uint256" }, { "internalType": "string", "name": "description", "type": "string" }], "name": "createSpendRequest", "outputs": [{ "internalType": "uint256", "name": "requestId", "type": "uint256" }], "stateMutability": "nonpayable", "type": "function" }, { "inputs": [], "name": "deposit", "outputs": [], "stateMutability": "payable", "type": "function" }, { "inputs": [{ "internalType": "uint256", "name": "refundId", "type": "uint256" }], "name": "executeRefundRequest", "outputs": [], "stateMutability": "nonpayable", "type": "function" }, { "inputs": [{ "internalType": "uint256", "name": "requestId", "type": "uint256" }], "name": "executeSpendRequest", "outputs": [], "stateMutability": "nonpayable", "type": "function" }, { "inputs": [{ "internalType": "uint256", "name": "refundId", "type": "uint256" }], "name": "expireRefundRequest", "outputs": [], "stateMutability": "nonpayable", "type": "function" }, { "inputs": [{ "internalType": "uint256", "name": "requestId", "type": "uint256" }], "name": "expireSpendRequest", "outputs": [], "stateMutability": "nonpayable", "type": "function" }, { "inputs": [], "name": "getAvailableClassFund", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" }, { "inputs": [], "name": "getFundBalance", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" }, { "inputs": [{ "internalType": "uint256", "name": "refundId", "type": "uint256" }], "name": "getRefundRequest", "outputs": [{ "internalType": "uint256", "name": "id", "type": "uint256" }, { "internalType": "address", "name": "applicant", "type": "address" }, { "internalType": "uint256", "name": "amount", "type": "uint256" }, { "internalType": "string", "name": "reason", "type": "string" }, { "internalType": "uint256", "name": "createdAt", "type": "uint256" }, { "internalType": "uint256", "name": "yesVotes", "type": "uint256" }, { "internalType": "uint256", "name": "noVotes", "type": "uint256" }, { "internalType": "enum ProjectCore.RequestStatus", "name": "status", "type": "uint8" }], "stateMutability": "view", "type": "function" }, { "inputs": [{ "internalType": "uint256", "name": "requestId", "type": "uint256" }], "name": "getSpendRequest", "outputs": [{ "internalType": "uint256", "name": "id", "type": "uint256" }, { "internalType": "address", "name": "recipient", "type": "address" }, { "internalType": "uint256", "name": "amount", "type": "uint256" }, { "internalType": "string", "name": "description", "type": "string" }, { "internalType": "address", "name": "creator", "type": "address" }, { "internalType": "uint256", "name": "createdAt", "type": "uint256" }, { "internalType": "uint256", "name": "yesVotes", "type": "uint256" }, { "internalType": "uint256", "name": "noVotes", "type": "uint256" }, { "internalType": "enum ProjectCore.RequestStatus", "name": "status", "type": "uint8" }], "stateMutability": "view", "type": "function" }, { "inputs": [{ "internalType": "address", "name": "student", "type": "address" }], "name": "getStudentAvailableContribution", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" }, { "inputs": [{ "internalType": "address", "name": "student", "type": "address" }], "name": "getStudentContribution", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" }, { "inputs": [], "name": "getTotalContractBalance", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" }, { "inputs": [{ "internalType": "uint256", "name": "requestId", "type": "uint256" }, { "internalType": "address", "name": "member", "type": "address" }], "name": "hasMemberVoted", "outputs": [{ "internalType": "bool", "name": "", "type": "bool" }], "stateMutability": "view", "type": "function" }, { "inputs": [{ "internalType": "uint256", "name": "refundId", "type": "uint256" }, { "internalType": "address", "name": "member", "type": "address" }], "name": "hasMemberVotedRefund", "outputs": [{ "internalType": "bool", "name": "", "type": "bool" }], "stateMutability": "view", "type": "function" }, { "inputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }, { "internalType": "address", "name": "", "type": "address" }], "name": "hasVoted", "outputs": [{ "internalType": "bool", "name": "", "type": "bool" }], "stateMutability": "view", "type": "function" }, { "inputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }, { "internalType": "address", "name": "", "type": "address" }], "name": "hasVotedRefund", "outputs": [{ "internalType": "bool", "name": "", "type": "bool" }], "stateMutability": "view", "type": "function" }, { "inputs": [{ "internalType": "address", "name": "", "type": "address" }], "name": "isBCSMember", "outputs": [{ "internalType": "bool", "name": "", "type": "bool" }], "stateMutability": "view", "type": "function" }, { "inputs": [{ "internalType": "address", "name": "", "type": "address" }], "name": "pendingStudentRefundAmount", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" }, { "inputs": [], "name": "refundRequestCount", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" }, { "inputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "name": "refundRequests", "outputs": [{ "internalType": "uint256", "name": "id", "type": "uint256" }, { "internalType": "address payable", "name": "applicant", "type": "address" }, { "internalType": "uint256", "name": "amount", "type": "uint256" }, { "internalType": "string", "name": "reason", "type": "string" }, { "internalType": "uint256", "name": "createdAt", "type": "uint256" }, { "internalType": "uint256", "name": "yesVotes", "type": "uint256" }, { "internalType": "uint256", "name": "noVotes", "type": "uint256" }, { "internalType": "enum ProjectCore.RequestStatus", "name": "status", "type": "uint8" }], "stateMutability": "view", "type": "function" }, { "inputs": [], "name": "reservedRefundAmount", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" }, { "inputs": [], "name": "reservedSpendAmount", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" }, { "inputs": [{ "internalType": "address", "name": "member", "type": "address" }, { "internalType": "bool", "name": "status", "type": "bool" }], "name": "setBCSMember", "outputs": [], "stateMutability": "nonpayable", "type": "function" }, { "inputs": [], "name": "spendRequestCount", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" }, { "inputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "name": "spendRequests", "outputs": [{ "internalType": "uint256", "name": "id", "type": "uint256" }, { "internalType": "address payable", "name": "recipient", "type": "address" }, { "internalType": "uint256", "name": "amount", "type": "uint256" }, { "internalType": "string", "name": "description", "type": "string" }, { "internalType": "address", "name": "creator", "type": "address" }, { "internalType": "uint256", "name": "createdAt", "type": "uint256" }, { "internalType": "uint256", "name": "yesVotes", "type": "uint256" }, { "internalType": "uint256", "name": "noVotes", "type": "uint256" }, { "internalType": "enum ProjectCore.RequestStatus", "name": "status", "type": "uint8" }], "stateMutability": "view", "type": "function" }, { "inputs": [{ "internalType": "address", "name": "", "type": "address" }], "name": "studentContributions", "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }], "stateMutability": "view", "type": "function" }, { "inputs": [{ "internalType": "uint256", "name": "refundId", "type": "uint256" }, { "internalType": "bool", "name": "support", "type": "bool" }], "name": "voteRefundRequest", "outputs": [], "stateMutability": "nonpayable", "type": "function" }, { "inputs": [{ "internalType": "uint256", "name": "requestId", "type": "uint256" }, { "internalType": "bool", "name": "support", "type": "bool" }], "name": "voteSpendRequest", "outputs": [], "stateMutability": "nonpayable", "type": "function" }, { "inputs": [{ "internalType": "uint256", "name": "amount", "type": "uint256" }], "name": "withdrawAdminFee", "outputs": [], "stateMutability": "nonpayable", "type": "function" }, { "stateMutability": "payable", "type": "receive" }];

    // --- 2. FAQ DATA ---
    const FAQ_DATA = [
      { cat: "Tổng quan", q: "KTS-Class-Fund là gì?", a: "KTS-Class-Fund là cổng thông tin và hệ thống quản lý quỹ lớp được xây dựng dựa trên Smart Contract (hợp đồng thông minh) trên nền tảng blockchain Ethereum Sepolia. Hệ thống giúp minh bạch hóa các khoản đóng góp, quản lý đề xuất chi tiêu và hoàn tiền cho tập thể sinh viên K57 ngành Kinh tế Số." },
      { cat: "Tổng quan", q: "Dự án giải quyết vấn đề gì?", a: "Dự án giải quyết những khó khăn khi quản lý quỹ thủ công như: thông tin thu chi nằm rải rác ở nhiều nơi, thành viên khó theo dõi một khoản chi do ai khởi xướng, khó kiểm chứng biên lai ngoài đời thực và người quản lý phải giải thích số liệu lặp đi lặp lại." },
      { cat: "Tổng quan", q: "Tại sao dùng Blockchain thay vì chỉ dùng bảng tính?", a: "Bảng tính thông thường có thể bị chỉnh sửa bất kỳ lúc nào mà không để lại vết tích rõ ràng. Trong khi đó, blockchain ghi nhận mọi giao dịch và kết quả bỏ phiếu một cách bất biến, công khai, giúp mọi thành viên đều có quyền kiểm chứng độc lập mà không cần đặt niềm tin mù quáng vào một cá nhân." },
      { cat: "Tổng quan", q: "Dữ liệu nào có thể kiểm tra công khai?", a: "Mọi thành viên đều có thể kiểm tra công khai: tổng số dư quỹ lớp, số dư quỹ phí vận hành, danh sách các đề nghị chi tiền, tiến độ bỏ phiếu tán thành của Ban cán sự và các giao dịch chuyển tiền đã được xác nhận trên Sepolia Etherscan." },
      { cat: "Tổng quan", q: "Hệ thống đang chạy trên Sepolia hay Mainnet?", a: "Hệ thống đang hoạt động trên mạng thử nghiệm Ethereum Sepolia Testnet. Mạng này hoàn toàn miễn phí, ETH sử dụng là tài sản thử nghiệm (SepoliaETH) không có giá trị tiền tệ thực tế, giúp sinh viên làm quen và thực hành công nghệ mà không gặp rủi ro tài chính." },

      { cat: "Ví và kết nối", q: "Tôi cần MetaMask để sử dụng website không?", a: "Nếu bạn chỉ muốn đọc tài liệu, tìm hiểu quy trình và xem hướng dẫn, bạn không cần cài MetaMask. Tuy nhiên, nếu bạn muốn nộp tiền vào quỹ, tạo đề nghị, tham gia biểu quyết hoặc xin hoàn tiền, bạn cần cài tiện ích ví MetaMask trên trình duyệt máy tính hoặc điện thoại." },
      { cat: "Ví và kết nối", q: "Vì sao website yêu cầu kết nối ví?", a: "Kết nối ví cho phép website xác định danh tính kỹ thuật (địa chỉ ví) của bạn để hiển thị đúng quyền hạn (Cố vấn, Ban cán sự hoặc Sinh viên) và giúp bạn tự tay ký xác nhận các giao dịch trên blockchain." },
      { cat: "Ví và kết nối", q: "Tại sao tôi phải chuyển sang mạng Sepolia?", a: "Hợp đồng thông minh của quỹ lớp được triển khai trên mạng thử nghiệm Ethereum Sepolia. Nếu ví của bạn đang kết nối ở mạng khác (như Ethereum Mainnet hay BNB Chain), các giao dịch sẽ không thể tương tác được với hợp đồng của lớp." },
      { cat: "Ví và kết nối", q: "Tôi có cần cung cấp mật khẩu, private key hoặc cụm từ khôi phục không?", a: "TUYỆT ĐỐI KHÔNG. Website không bao giờ hỏi hoặc yêu cầu bạn cung cấp mật khẩu ví, private key hay 12 từ khóa khôi phục (seed phrase). Bạn chỉ ký duyệt các giao dịch trực tiếp trên cửa sổ bảo mật của tiện ích MetaMask." },
      { cat: "Ví và kết nối", q: "Tôi làm gì nếu kết nối nhầm ví hoặc nhầm mạng?", a: "Bạn chỉ cần mở tiện ích MetaMask, bấm chọn đúng tài khoản mong muốn hoặc chuyển mạng sang Sepolia. Website sẽ tự động phát hiện và cập nhật trạng thái hiển thị ngay lập tức mà không cần tải lại trang." },

      { cat: "Đóng góp và phí", q: "Gửi tiền vào quỹ như thế nào?", a: "Bạn kết nối ví MetaMask, chuyển đến Ô Giao diện Sinh viên, nhập số ETH muốn đóng góp (ví dụ 0.05 ETH) và bấm nút 'Xác nhận nộp quỹ qua MetaMask'. Cửa sổ MetaMask sẽ hiện ra để bạn kiểm tra số tiền, phí gas và bấm 'Xác nhận'." },
      { cat: "Đóng góp và phí", q: "Vì sao MetaMask yêu cầu xác nhận giao dịch?", a: "MetaMask là người bảo vệ tài sản của bạn. Bất kỳ hành động nào làm thay đổi số dư hoặc gọi hợp đồng đều bắt buộc phải được chủ ví trực tiếp ký xác nhận mật mã học để tránh việc tiền bị chuyển đi trái phép." },
      { cat: "Đóng góp và phí", q: "Vì sao giao dịch cần gas?", a: "Phí gas là chi phí trả cho các máy chủ đào/xác thực trong mạng lưới Ethereum để xử lý và ghi nhận giao dịch vào khối. Trên mạng Sepolia, bạn có thể nhận SepoliaETH miễn phí từ các trang vòi (faucet) để trả phí gas này." },
      { cat: "Đóng góp và phí", q: "Tôi có thể hủy giao dịch sau khi đã xác nhận không?", a: "Khi một giao dịch đã được các khối blockchain xác nhận, dữ liệu trở thành vĩnh viễn và không thể đảo ngược. Do đó, hãy luôn kiểm tra kỹ số tiền và địa chỉ trước khi bấm xác nhận trên MetaMask." },
      { cat: "Đóng góp và phí", q: "Tại sao số tiền đóng góp và số tiền vào quỹ lớp có thể khác nhau?", a: "Theo quy định được lập trình trong hợp đồng, khi bạn nộp 100% số tiền thì 99% sẽ được đưa vào Quỹ lớp chính để phục vụ tập thể, còn 1% được tự động trích vào Quỹ phí vận hành để hỗ trợ chi phí gas cho ban quản trị." },
      { cat: "Đóng góp và phí", q: "Phần phí quản lý 1% được xử lý như thế nào?", a: "Khoản phí 1% được lưu trữ độc lập tại quỹ phí vận hành. Chỉ có Cố vấn học tập mới có quyền rút khoản phí này về ví để bù đắp chi phí gas khi thực hiện việc bổ nhiệm nhân sự và quản lý hệ thống." },

      { cat: "Đề xuất và biểu quyết", q: "Ai có quyền tạo đề xuất chi tiền?", a: "Chỉ các thành viên Ban cán sự đang hoạt động hợp lệ mới có quyền tạo đề nghị chi tiền. Khi tạo, người đề xuất phải ghi rõ số tiền, địa chỉ người nhận và mục đích chi tiêu cụ thể." },
      { cat: "Đề xuất và biểu quyết", q: "Khi nào đề xuất được thông qua?", a: "Đề nghị được thông qua khi đạt tỷ lệ đồng thuận tối thiểu từ 51% trở lên tính trên tổng số thành viên Ban cán sự đang hoạt động trong lớp, trong thời hạn quy định là 7 ngày." },
      { cat: "Đề xuất và biểu quyết", q: "Tại sao đề xuất đủ phiếu nhưng chưa được chuyển tiền?", a: "Khi đạt đủ 51% phiếu đồng ý, đề xuất mới chỉ chuyển sang trạng thái 'Đã đủ điều kiện giải ngân'. Để đảm bảo an toàn, cần một thành viên Ban cán sự bấm nút thực hiện giải ngân để hợp đồng thực hiện lệnh chuyển ETH đến người nhận." },
      { cat: "Đề xuất và biểu quyết", q: "Tôi có thể thay đổi phiếu sau khi đã bỏ phiếu không?", a: "Không thể thay đổi. Mỗi thành viên Ban cán sự chỉ được bỏ phiếu một lần duy nhất cho mỗi đề nghị để đảm bảo tính minh bạch và tránh gian lận biểu quyết." },
      { cat: "Đề xuất và biểu quyết", q: "Điều gì xảy ra khi hết hạn 7 ngày mà chưa đạt ngưỡng?", a: "Nếu quá 7 ngày mà đề nghị không đạt đủ 51% phiếu thuận, đề nghị sẽ hết hạn. Bất kỳ ai cũng có thể bấm dọn dẹp để hệ thống giải phóng khoản tiền đang tạm giữ về lại số dư khả dụng cho quỹ lớp." },
      { cat: "Đề xuất và biểu quyết", q: "Tôi có thể tạo hoặc bỏ phiếu nhiều lần không?", a: "Mỗi đề xuất chỉ được bỏ phiếu 1 lần đối với mỗi địa chỉ ví Ban cán sự. Cố ý bỏ phiếu lần 2 sẽ bị hợp đồng từ chối ngay lập tức." },

      { cat: "Hoàn tiền và lỗi giao dịch", q: "Khi nào tôi có thể gửi yêu cầu hoàn tiền?", a: "Khi bạn chuyển nhầm tiền hoặc đóng thừa vào quỹ lớp, bạn có thể gửi yêu cầu hoàn tiền trong Ô Giao diện Sinh viên. Số tiền xin hoàn không được vượt quá số tiền bạn đã thực sự đóng góp vào quỹ." },
      { cat: "Hoàn tiền và lỗi giao dịch", q: "Gửi yêu cầu hoàn tiền có đồng nghĩa với được hoàn tiền ngay không?", a: "Không. Để tránh việc kẻ xấu giả mạo rút trộm quỹ lớp, yêu cầu hoàn tiền phải được các thành viên Ban cán sự xem xét lý do và bỏ phiếu biểu quyết thông qua (tối thiểu 51%) trước khi được giải ngân." },
      { cat: "Hoàn tiền và lỗi giao dịch", q: "Vì sao sinh viên xin hoàn tiền lại chịu 1% phí?", a: "Quy tắc kinh tế của quỹ quy định khoản phí 1% khi nộp vào đã được tính cho quỹ vận hành hệ thống. Khi sinh viên nộp nhầm xin rút lại, sinh viên sẽ nhận lại 99% số tiền đã yêu cầu và chịu 1% phí này." },
      { cat: "Hoàn tiền và lỗi giao dịch", q: "Tôi phải làm gì nếu giao dịch pending (chờ xử lý) quá lâu?", a: "Giao dịch pending lâu thường do mạng Sepolia bị nghẽn hoặc mức phí gas quá thấp. Bạn có thể mở MetaMask, tìm giao dịch đang chờ và chọn nút 'Tăng tốc' (Speed up) để nâng phí gas giúp giao dịch được xác nhận nhanh hơn." },
      { cat: "Hoàn tiền và lỗi giao dịch", q: "Làm sao kiểm tra giao dịch đã thành công?", a: "Sau khi giao dịch hoàn tất, bạn có thể bấm vào liên kết mã băm giao dịch (Tx Hash) hiển thị trên màn hình để mở trang Sepolia Etherscan và xem dấu tích xanh 'Success'." },
      { cat: "Hoàn tiền và lỗi giao dịch", q: "Tôi cần làm gì nếu giao dịch thất bại?", a: "Nếu giao dịch thất bại (báo lỗi màu đỏ), bạn kiểm tra xem ví có đủ số dư SepoliaETH để trả phí gas không, bạn có đang kết nối đúng tài khoản có quyền thực hiện hay không, hoặc đọc thông báo lỗi chi tiết được hiển thị." },
      { cat: "Hoàn tiền và lỗi giao dịch", q: "Tôi có thể gửi yêu cầu hoàn tiền lần nữa sau khi yêu cầu cũ hết hạn không?", a: "Có thể. Khi yêu cầu hoàn tiền cũ bị hết hạn, số tiền giữ chỗ được giải phóng về hạn mức của bạn, cho phép bạn tạo một yêu cầu hoàn tiền mới nếu vẫn còn lý do chính đáng." }
    ];

    // --- 3. STATE VARIABLES ---
    let provider = null;
    let signer = null;
    let contract = null;
    let userAddress = null;
    let isAdvisor = false;
    let isBcsMember = false;
    // Danh bạ lớp K57 mặc định (khởi tạo ngoại tuyến & đồng bộ với backend)
    const DEFAULT_CLASS_ROSTER = [
      {
        mssv: "23K4300004",
        name: "Trần Hoàng Phương Dung",
        wallet: "0x78567A377559F0cB30173f93869326a82320159a",
        role: "bcs",
        roleTitle: "Ban cán sự"
      },
      {
        mssv: "23K4300015",
        name: "Võ Ngọc Tâm Phúc",
        wallet: "0xf5D971952dbDF69058a28D23110381d96B00cb50",
        role: "bcs",
        roleTitle: "Ban cán sự"
      },
      {
        mssv: "23K4300014",
        name: "Phan Thị Yến Nhi",
        wallet: "0x7Af21f18DEfDA4a141BAD89681C0d4767A42333C",
        role: "bcs",
        roleTitle: "Ban cán sự"
      },
      {
        mssv: "23K4300005",
        name: "Trần Thị Bình Dương",
        wallet: "0x64ADE1f3E814c98dEFeC19f07253afeBDD2DBfcf",
        role: "student",
        roleTitle: "Sinh viên"
      },
      {
        mssv: "23K4300025",
        name: "Nguyễn Thị Kim Chi",
        wallet: "0x372819EB492cc6A071b946d5b82BF46174FE8394",
        role: "student",
        roleTitle: "Sinh viên"
      }
    ];

    let classRoster = (() => {
      try {
        const cached = localStorage.getItem("kts_class_roster");
        if (cached) {
          const parsed = JSON.parse(cached);
          if (Array.isArray(parsed) && parsed.length > 0) return parsed;
        }
      } catch (e) { }
      return [...DEFAULT_CLASS_ROSTER];
    })();

    // --- 4. UTILITIES ---
    function shortenAddress(addr) {
      if (!addr || addr.length < 10) return addr || "";
      return addr.slice(0, 6) + "..." + addr.slice(-4);
    }

    function formatEth(weiVal) {
      if (!weiVal) return "0.0000";
      try {
        const val = ethers.formatEther(weiVal);
        return parseFloat(val).toFixed(4);
      } catch (e) {
        return "0.0000";
      }
    }

    function logToTerminal(msg) {
      const term = document.getElementById("terminalLog");
      if (!term) return;
      const timeStr = new Date().toLocaleTimeString();
      const newDiv = document.createElement("div");
      newDiv.style.marginBottom = "4px";
      newDiv.textContent = `[${timeStr}] ${msg}`;
      term.appendChild(newDiv);
      term.scrollTop = term.scrollHeight;
    }

    function clearTerminal() {
      const term = document.getElementById("terminalLog");
      if (term) term.innerHTML = "[Hệ thống] Nhật ký đã được xóa sạch.";
    }

    function showModal(title, htmlContent, customFooterHtml = null) {
      document.getElementById("modalTitle").textContent = title;
      document.getElementById("modalBody").innerHTML = htmlContent;
      const footer = document.getElementById("modalFooter");
      if (customFooterHtml) {
        footer.innerHTML = customFooterHtml;
      } else {
        footer.innerHTML = '<button class="btn btn-primary btn-sm" onclick="closeModal()">Đóng lại</button>';
      }
      document.getElementById("walletModal").classList.add("open");
    }

    function closeModal() {
      document.getElementById("walletModal").classList.remove("open");
    }

    function getStatusBadge(statusNum) {
      if (statusNum === 0) return '<span class="status-pill status-pending">Chờ biểu quyết</span>';
      if (statusNum === 1) return '<span class="status-pill status-ready">Đủ điều kiện</span>';
      if (statusNum === 2) return '<span class="status-pill status-executed">Đã thực hiện</span>';
      if (statusNum === 4) return '<span class="status-pill status-expired">Đã hết hạn</span>';
      return '<span class="status-pill status-expired">Không xác định</span>';
    }

    // Smart provider detector for MetaMask
    function getMetaMaskProvider() {
      if (typeof window === "undefined") return null;
      if (window.ethereum) {
        if (window.ethereum.providers && Array.isArray(window.ethereum.providers)) {
          const mm = window.ethereum.providers.find(p => p.isMetaMask);
          if (mm) return mm;
        }
        return window.ethereum;
      }
      return null;
    }

    // Prompt user to enter contract address if missing
    function promptContractConfig(actionName) {
      showModal(
        `Cấu hình Địa chỉ Hợp đồng để ${actionName}`,
        `<p style="margin-bottom:12px;">Bạn đã kết nối ví MetaMask thành công với địa chỉ <strong>${shortenAddress(userAddress)}</strong>.</p>
         <p style="margin-bottom:12px;">Tuy nhiên, hệ thống chưa có <strong>Địa chỉ Hợp đồng ProjectCore</strong> trên mạng Sepolia để thực hiện giao dịch này.</p>
         <div class="form-group" style="margin-bottom:16px;">
           <label for="inputModalContract">Dán địa chỉ Hợp đồng đã deploy (42 ký tự):</label>
           <input type="text" class="form-control" id="inputModalContract" placeholder="0x..." value="${CONFIG.contractAddress || ''}">
         </div>
         <p style="font-size:0.85rem; color:var(--text-muted);">Địa chỉ này sẽ được lưu tự động vào trình duyệt để bạn không cần nhập lại lần sau.</p>`,
        `<button class="btn btn-primary btn-sm" onclick="saveContractFromModal()">Lưu & Kích hoạt</button>
         <button class="btn btn-outline btn-sm" onclick="closeModal()">Đóng lại</button>`
      );
    }

    function saveContractFromModal() {
      const input = document.getElementById("inputModalContract");
      if (!input) return;
      const val = input.value.trim();
      if (!val || !ethers.isAddress(val)) {
        alert("Vui lòng nhập đúng định dạng địa chỉ hợp đồng Ethereum (42 ký tự, bắt đầu bằng 0x)!");
        return;
      }
      applyContractAddress(val);
      closeModal();
      alert("Đã cấu hình hợp đồng thành công! Bạn có thể thực hiện giao dịch ngay bây giờ.");
    }

    // --- 5. WORKSPACE VIEW MODE SWITCHER & 4 VAI TRÒ / DÒNG TIỀN ---
    let currentDetailRole = null; // 'student' | 'bcs' | 'advisor' | 'history' | null
    let allFlowItems = []; // Lưu trữ tất cả flow dòng tiền để lọc nhanh

    function selectRoleView(role) {
      const pStudent = document.getElementById("panelStudent");
      const pBCS = document.getElementById("panelBCS");
      const pAdvisor = document.getElementById("panelAdvisor");
      const pHistory = document.getElementById("panelHistory");

      const btnStudent = document.getElementById("btnRoleStudent");
      const btnBCS = document.getElementById("btnRoleBCS");
      const btnAdvisor = document.getElementById("btnRoleAdvisor");
      const btnHistory = document.getElementById("btnRoleHistory");

      const container = document.getElementById("roleDetailContainer");
      const hint = document.getElementById("roleDetailHint");

      // Nếu bấm lại vào chính nút đang mở -> toggle thu gọn
      if (currentDetailRole === role) {
        closeRoleDetail();
        return;
      }

      currentDetailRole = role;

      // Reset active buttons
      [btnStudent, btnBCS, btnAdvisor, btnHistory].forEach(b => {
        if (b) b.classList.remove("active");
      });

      // Hide all panels initially
      [pStudent, pBCS, pAdvisor, pHistory].forEach(p => {
        if (p) p.style.display = "none";
      });

      if (container) container.style.display = "block";

      if (role === "student") {
        if (btnStudent) btnStudent.classList.add("active");
        if (pStudent) pStudent.style.display = "flex";
        if (hint) hint.innerHTML = '<span>Đang mở <strong>Ô Chi Tiết: Sinh Viên</strong> (Bấm lại nút để thu gọn)</span>';
      } else if (role === "bcs") {
        if (btnBCS) btnBCS.classList.add("active");
        if (pBCS) pBCS.style.display = "flex";
        if (hint) hint.innerHTML = '<span>Đang mở <strong>Ô Chi Tiết: Ban Cán Sự</strong> (Bấm lại nút để thu gọn)</span>';
      } else if (role === "advisor") {
        if (btnAdvisor) btnAdvisor.classList.add("active");
        if (pAdvisor) pAdvisor.style.display = "flex";
        if (hint) hint.innerHTML = '<span>Đang mở <strong>Ô Chi Tiết: Cố Vấn Học Tập</strong> (Bấm lại nút để thu gọn)</span>';
      } else if (role === "history") {
        if (btnHistory) btnHistory.classList.add("active");
        if (pHistory) {
          pHistory.style.display = "flex";
          renderFlowLedgerTable(allFlowItems);
        }
        if (hint) hint.innerHTML = '<span>Đang mở <strong>Ô Chi Tiết: Lịch Sử Dòng Tiền & Toàn Bộ Flow</strong> (Bấm lại nút để thu gọn)</span>';

        // Nếu có hợp đồng mà dữ liệu chưa tải, tự động tải lại
        if (contract && allFlowItems.length === 0) {
          refreshContractData();
        }
      }

      // Smooth scroll into detail box if needed
      container.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    function closeRoleDetail() {
      currentDetailRole = null;
      const pStudent = document.getElementById("panelStudent");
      const pBCS = document.getElementById("panelBCS");
      const pAdvisor = document.getElementById("panelAdvisor");
      const pHistory = document.getElementById("panelHistory");

      const btnStudent = document.getElementById("btnRoleStudent");
      const btnBCS = document.getElementById("btnRoleBCS");
      const btnAdvisor = document.getElementById("btnRoleAdvisor");
      const btnHistory = document.getElementById("btnRoleHistory");

      const container = document.getElementById("roleDetailContainer");
      const hint = document.getElementById("roleDetailHint");

      [btnStudent, btnBCS, btnAdvisor, btnHistory].forEach(b => {
        if (b) b.classList.remove("active");
      });

      [pStudent, pBCS, pAdvisor, pHistory].forEach(p => {
        if (p) p.style.display = "none";
      });

      if (container) container.style.display = "none";

      if (hint) hint.innerHTML = '💡 Bấm vào một trong 4 nút trên để mở ô chi tiết và theo dõi dòng tiền.';
    }

    // Hàm tương thích ngược cho các lời gọi cũ
    function setWorkspaceView(viewMode) {
      if (viewMode === "all") {
        selectRoleView("student");
      } else {
        selectRoleView(viewMode);
      }
    }

    // --- 6. RENDER FAQ & CALCULATOR ---
    // State for FAQ display
    let currentFaqCategory = "all";
    let isFaqExpanded = false; // default compact (only 4 items)
    let areAllFaqOpen = false;

    function setFaqCategory(cat) {
      currentFaqCategory = cat;
      isFaqExpanded = false; // reset to compact when changing category
      document.querySelectorAll(".faq-cat-btn").forEach(btn => {
        const text = btn.textContent;
        if ((cat === "all" && text.startsWith("Tất cả")) || (cat !== "all" && text.includes(cat))) {
          btn.classList.add("active");
        } else {
          btn.classList.remove("active");
        }
      });
      applyFaqFilter();
    }

    function toggleFaqLength() {
      isFaqExpanded = !isFaqExpanded;
      applyFaqFilter();
    }

    function toggleAllFaq() {
      areAllFaqOpen = !areAllFaqOpen;
      const items = document.querySelectorAll("#faqAccordionContainer .accordion-item");
      items.forEach(el => {
        if (areAllFaqOpen) {
          el.classList.add("open");
        } else {
          el.classList.remove("open");
        }
      });
      const btn = document.getElementById("btnToggleAllFaq");
      if (btn) btn.textContent = areAllFaqOpen ? "Thu gọn tất cả ▴" : "Mở rộng tất cả ▾";
    }

    function applyFaqFilter() {
      const searchInput = document.getElementById("faqSearchInput");
      const keyword = (searchInput ? searchInput.value : "").trim().toLowerCase();

      let list = FAQ_DATA;
      if (currentFaqCategory !== "all") {
        list = list.filter(item => item.cat === currentFaqCategory);
      }

      if (keyword) {
        list = list.filter(item => 
          item.q.toLowerCase().includes(keyword) || 
          item.a.toLowerCase().includes(keyword) ||
          item.cat.toLowerCase().includes(keyword)
        );
      }

      renderFaq(list);
    }

    function renderFaq(faqList) {
      const container = document.getElementById("faqAccordionContainer");
      const showMoreWrapper = document.getElementById("faqShowMoreWrapper");
      const showMoreBtn = document.getElementById("btnToggleFaqLength");
      if (!container) return;

      if (faqList.length === 0) {
        container.innerHTML = '<div style="text-align:center; padding:30px; color:var(--text-muted); background:#fff; border-radius:12px; border:1px solid #e2e8f0;">Không tìm thấy câu hỏi nào phù hợp với từ khóa tìm kiếm.</div>';
        if (showMoreWrapper) showMoreWrapper.style.display = "none";
        return;
      }

      const totalItems = faqList.length;
      const compactLimit = 4;
      const shouldLimit = !isFaqExpanded && totalItems > compactLimit;
      const displayItems = shouldLimit ? faqList.slice(0, compactLimit) : faqList;

      let html = "";
      displayItems.forEach((item, index) => {
        html += `
          <div class="accordion-item" id="faq-item-${index}">
            <div class="accordion-header" onclick="toggleFaq(${index})">
              <span><span class="faq-cat-badge">${item.cat}</span> ${item.q}</span>
              <span class="accordion-icon">▾</span>
            </div>
            <div class="accordion-body">
              ${item.a}
            </div>
          </div>
        `;
      });
      container.innerHTML = html;

      // Handle "Xem thêm / Thu gọn" button state
      if (showMoreWrapper && showMoreBtn) {
        if (totalItems <= compactLimit) {
          showMoreWrapper.style.display = "none";
        } else {
          showMoreWrapper.style.display = "block";
          if (isFaqExpanded) {
            showMoreBtn.innerHTML = `<span>Thu gọn bớt câu hỏi ▴</span>`;
          } else {
            showMoreBtn.innerHTML = `<span>Xem thêm ${totalItems - compactLimit} câu hỏi khác ▾</span>`;
          }
        }
      }
    }

    function toggleFaq(index) {
      const item = document.getElementById(`faq-item-${index}`);
      if (!item) return;
      const isOpen = item.classList.contains("open");
      // Optional: If accordion style, close others, or allow multiple open
      // Let's toggle smoothly:
      if (isOpen) {
        item.classList.remove("open");
      } else {
        item.classList.add("open");
      }
    }

    function setupCalculator() {
      const input = document.getElementById("calcInputEth");
      if (!input) return;
      input.addEventListener("input", () => {
        const val = parseFloat(input.value) || 0;
        const classFund = val * 0.99;
        const adminFee = val * 0.01;
        document.getElementById("calcClassFund").textContent = classFund.toFixed(4) + " ETH";
        document.getElementById("calcAdminFee").textContent = adminFee.toFixed(4) + " ETH";
        document.getElementById("calcMaxRefund").textContent = classFund.toFixed(4) + " ETH";
      });
    }

    // --- 7. METAMASK & WEB3 INTEGRATION ---
    async function initWeb3() {
      // Cơ chế chống ghi đè (Anti-override & Auto-migration):
      // So sánh địa chỉ deploy chuẩn trong code với địa chỉ deploy đã lưu lần trước.
      const savedDefault = localStorage.getItem("kts_deployed_contract_default");
      const savedAddr = localStorage.getItem("kts_class_fund_contract");

      if (CONFIG.defaultContractAddress && CONFIG.defaultContractAddress !== savedDefault) {
        // Phát hiện mã nguồn vừa cập nhật bản deploy mới -> Tự động đồng bộ & xóa cache người nộp cũ
        logToTerminal(`[Hệ thống] Phát hiện phiên bản hợp đồng mới từ dự án: ${shortenAddress(CONFIG.defaultContractAddress)}. Tự động đồng bộ...`);
        localStorage.setItem("kts_deployed_contract_default", CONFIG.defaultContractAddress);
        localStorage.setItem("kts_class_fund_contract", CONFIG.defaultContractAddress);
        localStorage.removeItem("kts_known_depositors");
        CONFIG.contractAddress = CONFIG.defaultContractAddress;
      } else if (savedAddr && ethers.isAddress(savedAddr)) {
        CONFIG.contractAddress = savedAddr;
        logToTerminal(`[Bộ nhớ] Đã tải địa chỉ hợp đồng đã lưu: ${shortenAddress(savedAddr)}`);
      } else if (CONFIG.defaultContractAddress && ethers.isAddress(CONFIG.defaultContractAddress)) {
        CONFIG.contractAddress = CONFIG.defaultContractAddress;
      }

      const quickInp = document.getElementById("quickContractAddress");
      const configInp = document.getElementById("configContractAddress");
      if (quickInp) quickInp.value = CONFIG.contractAddress || "";
      if (configInp) configInp.value = CONFIG.contractAddress || "";

      const eth = getMetaMaskProvider();
      if (eth) {
        provider = new ethers.BrowserProvider(eth);

        eth.on("accountsChanged", (accounts) => {
          if (!accounts || accounts.length === 0) {
            handleDisconnect();
          } else {
            handleAccountChange(accounts[0]);
          }
        });

        eth.on("chainChanged", () => {
          window.location.reload();
        });

        logToTerminal("[Khởi tạo] Tiện ích MetaMask đã sẵn sàng kết nối.");

        // Tự động khôi phục tài khoản nếu ví đã từng kết nối trước đó (Silent reconnect)
        try {
          const preAccounts = await eth.request({ method: "eth_accounts" });
          if (preAccounts && preAccounts.length > 0) {
            await handleAccountChange(preAccounts[0]);
          }
        } catch (e) {
          console.warn("Silent eth_accounts error:", e);
        }
      } else {
        logToTerminal("[Lưu ý] Chưa phát hiện tiện ích MetaMask trên trình duyệt.");
      }

      // Nếu ví chưa kết nối nhưng đã có địa chỉ hợp đồng, tự động tải dữ liệu on-chain ở chế độ đọc
      if (!contract && CONFIG.contractAddress && ethers.isAddress(CONFIG.contractAddress)) {
        try {
          if (!provider) {
            provider = new ethers.JsonRpcProvider("https://ethereum-sepolia-rpc.publicnode.com");
          }
          await initContractInstance();
        } catch (readErr) {
          console.warn("Fallback read contract instance error:", readErr);
        }
      }
    }

    async function switchAccount() {
      const eth = getMetaMaskProvider();
      if (!eth) {
        alert("Chưa phát hiện tiện ích ví MetaMask trên trình duyệt!");
        return;
      }
      try {
        logToTerminal("[MetaMask] Đang mở hộp thoại chọn đổi tài khoản trên MetaMask...");
        await eth.request({
          method: "wallet_requestPermissions",
          params: [{ eth_accounts: {} }]
        });
        const accounts = await eth.request({ method: "eth_accounts" });
        if (accounts && accounts.length > 0) {
          await handleAccountChange(accounts[0]);
          logToTerminal(`[Thành công] Đã chuyển đổi sang tài khoản ví: ${accounts[0]}`);
          alert("Đã chuyển đổi sang tài khoản ví: " + accounts[0]);
        }
      } catch (err) {
        if (err.code === 4001) {
          logToTerminal("[Thông báo] Bạn đã đóng cửa sổ chọn đổi tài khoản.");
        } else {
          logToTerminal("[Lỗi đổi ví] " + (err.shortMessage || err.message));
          disconnectWallet();
        }
      }
    }

    function disconnectWallet() {
      handleDisconnect();
      logToTerminal("[MetaMask] Đã ngắt kết nối ví. Bạn có thể mở MetaMask chọn tài khoản khác rồi bấm 'Kết nối MetaMask'.");
      alert("Đã ngắt kết nối ví trên website! Bây giờ bạn có thể mở MetaMask trên trình duyệt, bấm chọn tài khoản khác rồi bấm 'Kết nối MetaMask'.");
    }

    async function connectWallet() {
      if (userAddress) {
        await switchAccount();
        return;
      }
      const eth = getMetaMaskProvider();

      if (!eth) {
        if (window.location.protocol === "file:") {
          showModal(
            "Cần cấu hình tiện ích cho tệp cục bộ (file://)",
            `<p>Bạn đang mở website trực tiếp từ ổ đĩa máy tính (giao thức <code>file:///...</code>). Theo chính sách bảo mật, trình duyệt mặc định không cho phép MetaMask hoạt động trên tệp cục bộ.</p>
             <h4 style="margin: 14px 0 8px 0; color:var(--brand-blue);">Cách xử lý đơn giản (Chọn 1 trong 2 cách):</h4>
             <div style="background:#f1f5f9; padding:12px; border-radius:8px; margin-bottom:12px;">
               <strong>Cách 1 (Khuyên dùng nhất):</strong> Chạy máy chủ cục bộ bằng lệnh terminal:<br>
               <code style="display:block; background:#0f172a; color:#38bdf8; padding:8px; border-radius:4px; margin-top:6px;">npx serve web</code>
               sau đó mở địa chỉ: <strong>http://localhost:3000</strong> trên trình duyệt.
             </div>
             <div style="background:#f1f5f9; padding:12px; border-radius:8px;">
               <strong>Cách 2 (Mở trực tiếp tệp):</strong> Vào cài đặt trình duyệt &rarr; Quản lý tiện ích (<code>chrome://extensions</code>) &rarr; Tìm <strong>MetaMask</strong> &rarr; Bấm <strong>Chi tiết</strong> (Details) &rarr; Bật nút <strong>"Cho phép truy cập vào các URL của tệp"</strong> (Allow access to file URLs) &rarr; Tải lại trang (F5).
             </div>`
          );
        } else {
          showModal(
            "Chưa cài đặt tiện ích ví MetaMask",
            `<p>Để tương tác với hợp đồng thông minh, bạn cần cài đặt tiện ích mở rộng ví MetaMask miễn phí trên trình duyệt của bạn.</p>
             <p style="margin: 16px 0;">Vui lòng truy cập trang chủ chính thức của MetaMask để tải và cài đặt tiện ích:</p>
             <a href="https://metamask.io/download/" target="_blank" class="btn btn-primary" style="display:inline-block; margin-bottom:12px;">Tải MetaMask chính thức tại metamask.io &rarr;</a>
             <p style="font-size:0.85rem; color:var(--text-muted);">Sau khi cài đặt xong, hãy tạo ví và tải lại trang này để bấm nút Kết nối.</p>`
          );
        }
        return;
      }

      try {
        logToTerminal("[MetaMask] Đang gửi yêu cầu kết nối tài khoản ví...");
        provider = new ethers.BrowserProvider(eth);
        const accounts = await provider.send("eth_requestAccounts", []);
        if (accounts && accounts.length > 0) {
          await handleAccountChange(accounts[0]);
        }
      } catch (err) {
        if (err.code === 4001 || (err.message && err.message.includes("rejected"))) {
          logToTerminal("[Thông báo] Bạn đã từ chối yêu cầu kết nối trên MetaMask.");
          alert("Bạn đã hủy kết nối ví. Khi bạn sẵn sàng, vui lòng bấm lại nút 'Kết nối MetaMask' để sử dụng.");
        } else if (err.code === -32002) {
          logToTerminal("[Cảnh báo] MetaMask đang có một cửa sổ chờ mở khóa.");
          alert("Cửa sổ MetaMask đang mở yêu cầu kết nối. Vui lòng bấm vào biểu tượng con cáo MetaMask trên góc trình duyệt để nhập mật khẩu.");
        } else {
          logToTerminal("[Lỗi kết nối] " + (err.shortMessage || err.message));
          alert("Không thể kết nối ví: " + (err.shortMessage || err.message));
        }
      }
    }

    async function handleDisconnect() {
      userAddress = null;
      signer = null;
      contract = null;
      isAdvisor = false;
      isBcsMember = false;
      myStudentProfile = null;
      document.getElementById("walletBtnText").textContent = "Kết nối MetaMask";
      document.getElementById("networkDot").className = "badge-dot";
      document.getElementById("networkText").textContent = "Chưa kết nối ví";
      document.getElementById("quickWalletAccount").textContent = "Chưa kết nối ví";
      updateRoleDisplay("none");
      const bSwitch = document.getElementById("btnSwitchWallet");
      const bDisc = document.getElementById("btnDisconnectWallet");
      const bQSwitch = document.getElementById("btnQuickSwitch");
      const bQDisc = document.getElementById("btnQuickDisconnect");
      if (bSwitch) bSwitch.style.display = "none";
      if (bDisc) bDisc.style.display = "none";
      if (bQSwitch) bQSwitch.style.display = "none";
      if (bQDisc) bQDisc.style.display = "none";
      logToTerminal("[MetaMask] Đã ngắt kết nối tài khoản.");
    }

    async function handleAccountChange(account) {
      userAddress = account;
      signer = await provider.getSigner();

      // Kiểm tra mạng
      const network = await provider.getNetwork();
      const chainId = Number(network.chainId);

      const netBadge = document.getElementById("networkText");
      const netDot = document.getElementById("networkDot");

      if (chainId === CONFIG.chainId) {
        netDot.className = "badge-dot connected";
        netBadge.textContent = "Sepolia (11155111)";
        document.getElementById("quickNetworkStatus").textContent = "Sepolia (11155111)";
        logToTerminal(`[Mạng lưới] Đã kết nối đúng mạng Ethereum Sepolia.`);
      } else {
        netDot.className = "badge-dot error";
        netBadge.textContent = "Sai mạng (" + chainId + ")";
        document.getElementById("quickNetworkStatus").textContent = `Sai mạng (Hiện tại: ${chainId} - Yêu cầu: 11155111)`;
        logToTerminal(`[Cảnh báo] Bạn đang ở mạng Chain ID: ${chainId}. Hệ thống cần mạng Ethereum Sepolia (11155111).`);
        promptSwitchSepoliaModal(chainId);
      }

      document.getElementById("walletBtnText").textContent = shortenAddress(account);
      document.getElementById("quickWalletAccount").textContent = shortenAddress(account);
      const bSwitch = document.getElementById("btnSwitchWallet");
      const bDisc = document.getElementById("btnDisconnectWallet");
      const bQSwitch = document.getElementById("btnQuickSwitch");
      const bQDisc = document.getElementById("btnQuickDisconnect");
      if (bSwitch) bSwitch.style.display = "inline-flex";
      if (bDisc) bDisc.style.display = "inline-flex";
      if (bQSwitch) bQSwitch.style.display = "inline-flex";
      if (bQDisc) bQDisc.style.display = "inline-flex";

      const student = await checkMyStudentIdentity(userAddress);
      const isKnownAdvisor = (
        (userAddress && userAddress.toLowerCase() === "0x36fd4887e9d1eca4ae5062a745cc2c6182b77060".toLowerCase()) ||
        (student && student.role === "advisor")
      );

      if (isKnownAdvisor) {
        isAdvisor = true;
        isBcsMember = false;
        updateRoleDisplay("advisor", null);
        logToTerminal(`[Tài khoản] Đã kết nối: Cố vấn học tập K57 - ${shortenAddress(account)}`);
        loadClassRoster(userAddress);
      } else if (student) {
        if (student.role === "bcs") {
          isBcsMember = true;
        }
        updateRoleDisplay(student.role === "bcs" ? "bcs" : "student", student);
        logToTerminal(`[Tài khoản] Đã kết nối: ${student.name} (${student.mssv}) - ${shortenAddress(account)}`);
        if (student.role === "bcs") {
          loadClassRoster(userAddress);
        }
      } else {
        updateRoleDisplay("guest", null);
        const sbId = document.getElementById("sidebarUserIdentity");
        const sbRole = document.getElementById("sidebarRoleBadge");
        const sbAddr = document.getElementById("sidebarWalletShort");
        if (sbId) sbId.textContent = "Chưa kết nối ví";
        if (sbRole) { sbRole.textContent = "Chưa kết nối"; sbRole.className = "status-pill status-ready"; sbRole.style.background = ""; sbRole.style.color = ""; }
        if (sbAddr) sbAddr.textContent = "--";
        logToTerminal(`[Tài khoản] Đã kết nối ví: ${shortenAddress(account)} (Chưa có trong danh bạ K57)`);
      }

      // Initialize contract if address available
      if (CONFIG.contractAddress && ethers.isAddress(CONFIG.contractAddress)) {
        await initContractInstance();
      }
    }

    function promptSwitchSepoliaModal(currentChain) {
      showModal(
        "Chuyển sang mạng Ethereum Sepolia",
        `<p>Hệ thống KTS Class Fund hoạt động trên mạng thử nghiệm <strong>Ethereum Sepolia</strong> (Chain ID: 11155111).</p>
         <p style="margin: 12px 0;">Hiện tại ví của bạn đang kết nối ở mạng có Chain ID là <strong>${currentChain}</strong>.</p>
         <p>Vui lòng bấm nút bên dưới để MetaMask chuyển sang mạng Sepolia:</p>
         <div style="margin-top: 16px;">
           <button class="btn btn-warning" onclick="doSwitchSepolia()">Chuyển sang mạng Sepolia trên MetaMask</button>
         </div>`
      );
    }

    async function doSwitchSepolia() {
      const eth = getMetaMaskProvider();
      if (!eth) return;
      try {
        await eth.request({
          method: "wallet_switchEthereumChain",
          params: [{ chainId: CONFIG.chainIdHex }]
        });
        closeModal();
      } catch (switchError) {
        if (switchError.code === 4902) {
          try {
            await eth.request({
              method: "wallet_addEthereumChain",
              params: [{
                chainId: CONFIG.chainIdHex,
                chainName: CONFIG.chainName,
                nativeCurrency: { name: "Sepolia ETH", symbol: "SEP", decimals: 18 },
                rpcUrls: ["https://rpc.sepolia.org"],
                blockExplorerUrls: [CONFIG.blockExplorer]
              }]
            });
            closeModal();
          } catch (addError) {
            logToTerminal("[Lỗi] Không thể thêm mạng Sepolia vào MetaMask.");
          }
        }
      }
    }

    // --- ROSTER MANAGEMENT & PRIVACY PROTECTION ---
    let myStudentProfile = null;

    async function checkMyStudentIdentity(address) {
      if (!address) return null;
      try {
        const res = await fetch(`http://localhost:8000/api/roster/check?address=${encodeURIComponent(address)}`);
        if (res.ok) {
          const data = await res.json();
          if (data && data.success && data.isMember && data.student) {
            myStudentProfile = data.student;
            return data.student;
          }
        }
      } catch (e) {
        console.warn("Lỗi kiểm tra danh tính:", e);
      }
      return null;
    }

    async function loadClassRoster(signerAddr = null) {
      const caller = signerAddr || userAddress || "";
      const isBcs = isBcsMember || (myStudentProfile && myStudentProfile.role === "bcs");
      try {
        const res = await fetch(`http://localhost:8000/api/roster?address=${encodeURIComponent(caller)}&isBcs=${isBcs ? '1' : '0'}&isAdvisor=${isAdvisor ? '1' : '0'}`);
        if (res.ok) {
          const data = await res.json();
          if (data && data.success && Array.isArray(data.roster) && data.roster.length > 0) {
            classRoster = data.roster;
            try { localStorage.setItem("kts_class_roster", JSON.stringify(classRoster)); } catch(e){}
          }
        }
      } catch (err) {
        console.warn("Chưa thể tải danh bạ từ backend, sử dụng danh bạ cục bộ:", err);
      }

      // Cập nhật số lượng trên cả 2 vị trí badge (modal và topbar)
      const countBadge = document.getElementById("rosterCountBadge");
      if (countBadge) countBadge.textContent = classRoster.length;
      const sbBadge = document.getElementById("sidebarRosterBadge");
      if (sbBadge) sbBadge.textContent = classRoster.length;

      renderRosterTable();
      renderAnnouncementUI(); // Tự động cập nhật sĩ số lớp và tiến độ nộp quỹ theo danh bạ mới nhất

      if (userAddress) {
        const s = lookupStudent(userAddress);
        if (s) {
          myStudentProfile = s;
          if (s.role === "bcs") isBcsMember = true;
          updateRoleDisplay(isAdvisor ? "advisor" : (s.role === "bcs" ? "bcs" : "student"), s);
        }
      }
      return classRoster;
    }

    function lookupStudent(addr) {
      if (!addr) return null;
      const target = addr.toLowerCase().trim();
      if (myStudentProfile && myStudentProfile.wallet && myStudentProfile.wallet.toLowerCase().trim() === target) {
        return myStudentProfile;
      }
      if (classRoster && classRoster.length > 0) {
        const found = classRoster.find(s => s.wallet && s.wallet.toLowerCase().trim() === target);
        if (found) return found;
      }
      return DEFAULT_CLASS_ROSTER.find(s => s.wallet && s.wallet.toLowerCase().trim() === target) || null;
    }

    function openRosterModal() {
      const isBcs = isBcsMember || (myStudentProfile && myStudentProfile.role === "bcs");
      const canManage = isAdvisor || isBcs;

      const modal = document.getElementById("rosterModal");
      const adminSec = document.getElementById("rosterAdminSection");
      const bcsNote = document.getElementById("rosterBcsViewNote");

      // Cả Cố vấn học tập và Ban cán sự đều có quyền thêm/sửa địa chỉ ví sinh viên
      if (adminSec) {
        adminSec.style.display = canManage ? "block" : "none";
      }
      if (bcsNote) {
        if (canManage) {
          bcsNote.style.display = "block";
          bcsNote.innerHTML = isAdvisor
            ? "🏛️ <strong>Tài khoản Cố vấn học tập:</strong> Bạn có quyền thêm mới, xóa và cập nhật danh bạ sinh viên K57."
            : "⭐ <strong>Tài khoản Ban cán sự:</strong> Bạn có quyền thêm mới, cập nhật MSSV và địa chỉ ví sinh viên để đối soát nộp quỹ.";
        } else {
          bcsNote.style.display = "none";
        }
      }

      if (modal) {
        modal.classList.add("open");
        modal.classList.add("show");

        // Đặt lại ô tìm kiếm và bộ lọc về Tất cả mỗi khi mở
        const searchInput = document.getElementById("rosterSearchInput");
        if (searchInput) searchInput.value = "";
        currentRosterFilter = "all";
        ["rfFilterAll", "rfFilterBcs", "rfFilterStudent", "rfFilterPaid", "rfFilterUnpaid"].forEach(id => {
          const btn = document.getElementById(id);
          if (btn) {
            if (id === "rfFilterAll") btn.classList.add("active");
            else btn.classList.remove("active");
          }
        });

        if (!classRoster || classRoster.length === 0) {
          loadClassRoster(userAddress);
        } else {
          renderRosterTable();
        }
      }
    }

    function closeRosterModal() {
      const modal = document.getElementById("rosterModal");
      if (modal) {
        modal.classList.remove("open");
        modal.classList.remove("show");
      }
      cancelEditRoster();
    }

    let currentEditingMssv = null;

    function editRosterStudent(mssv) {
      const isBcs = isBcsMember || (myStudentProfile && myStudentProfile.role === "bcs");
      if (!isAdvisor && !isBcs) {
        alert("Chỉ Ban cán sự hoặc Cố vấn học tập mới có quyền chỉnh sửa thông tin sinh viên!");
        return;
      }
      const s = classRoster.find(item => item.mssv === mssv);
      if (!s) return;
      currentEditingMssv = s.mssv;

      const fMssv = document.getElementById("formRosterMssv");
      const fName = document.getElementById("formRosterName");
      const fWallet = document.getElementById("formRosterWallet");
      const fRole = document.getElementById("formRosterRole");
      const fTitle = document.getElementById("rosterFormTitle");
      const btnSave = document.getElementById("btnSaveRosterEntry");
      const btnCancel = document.getElementById("btnCancelEditRoster");
      const adminSec = document.getElementById("rosterAdminSection");

      if (fMssv) fMssv.value = s.mssv;
      if (fName) fName.value = s.name;
      if (fWallet) fWallet.value = s.wallet;
      if (fRole) fRole.value = (s.role === "bcs") ? "bcs|Ban cán sự" : "student|Sinh viên";

      if (fTitle) {
        fTitle.innerHTML = `<span>✏️</span> Chỉnh sửa sinh viên: <strong>${s.name}</strong> (${s.mssv})`;
      }
      if (btnSave) {
        btnSave.textContent = "💾 Cập nhật thay đổi";
      }
      if (btnCancel) {
        btnCancel.style.display = "inline-flex";
      }
      if (adminSec) {
        adminSec.style.display = "block";
        adminSec.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }

    let currentRosterFilter = "all";
    const rosterContribCache = new Map();

    function setRosterFilter(filterName) {
      currentRosterFilter = filterName;
      const btnIds = {
        all: "rfFilterAll",
        bcs: "rfFilterBcs",
        student: "rfFilterStudent",
        paid: "rfFilterPaid",
        unpaid: "rfFilterUnpaid"
      };
      Object.keys(btnIds).forEach(key => {
        const btn = document.getElementById(btnIds[key]);
        if (btn) {
          if (key === filterName) btn.classList.add("active");
          else btn.classList.remove("active");
        }
      });
      renderRosterTable();
    }

    function filterRosterTable() {
      renderRosterTable();
    }

    function getRosterAvatarGradient(str) {
      const gradients = [
        "linear-gradient(135deg, #6366f1 0%, #a855f7 100%)",
        "linear-gradient(135deg, #0284c7 0%, #38bdf8 100%)",
        "linear-gradient(135deg, #059669 0%, #34d399 100%)",
        "linear-gradient(135deg, #d97706 0%, #fbbf24 100%)",
        "linear-gradient(135deg, #e11d48 0%, #fb7185 100%)",
        "linear-gradient(135deg, #7c3aed 0%, #c084fc 100%)",
        "linear-gradient(135deg, #0d9488 0%, #2dd4bf 100%)",
        "linear-gradient(135deg, #4f46e5 0%, #818cf8 100%)"
      ];
      let hash = 0;
      for (let i = 0; i < (str || "").length; i++) {
        hash = (hash << 5) - hash + str.charCodeAt(i);
        hash |= 0;
      }
      return gradients[Math.abs(hash) % gradients.length];
    }

    function getInitials(name) {
      if (!name) return "SV";
      const parts = name.trim().split(/\s+/);
      if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
      return (parts[parts.length - 2][0] + parts[parts.length - 1][0]).toUpperCase();
    }

    function copyRosterWallet(addr, btnEl) {
      if (!addr) return;
      const doSuccess = () => {
        const origText = btnEl.innerHTML;
        btnEl.innerHTML = "✓ Đã chép!";
        btnEl.style.color = "#16a34a";
        btnEl.style.borderColor = "#86efac";
        btnEl.style.background = "#f0fdf4";
        setTimeout(() => {
          btnEl.innerHTML = origText;
          btnEl.style.color = "";
          btnEl.style.borderColor = "";
          btnEl.style.background = "";
        }, 1800);
      };

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(addr).then(doSuccess).catch(() => {
          fallbackCopyText(addr, doSuccess);
        });
      } else {
        fallbackCopyText(addr, doSuccess);
      }
    }

    function fallbackCopyText(text, callback) {
      const inp = document.createElement("input");
      inp.value = text;
      document.body.appendChild(inp);
      inp.select();
      try {
        document.execCommand("copy");
        if (callback) callback();
      } catch (e) {
        alert("Địa chỉ ví: " + text);
      }
      document.body.removeChild(inp);
    }

    function cancelEditRoster() {
      currentEditingMssv = null;
      const fMssv = document.getElementById("formRosterMssv");
      const fName = document.getElementById("formRosterName");
      const fWallet = document.getElementById("formRosterWallet");
      const fRole = document.getElementById("formRosterRole");
      const fTitle = document.getElementById("rosterFormTitle");
      const btnSave = document.getElementById("btnSaveRosterEntry");
      const btnCancel = document.getElementById("btnCancelEditRoster");

      if (fMssv) fMssv.value = "";
      if (fName) fName.value = "";
      if (fWallet) fWallet.value = "";
      if (fRole) fRole.value = "student|Sinh viên";

      if (fTitle) {
        fTitle.innerHTML = `<span>➕</span> Đăng ký / Cập nhật liên kết ví sinh viên (Dành riêng cho Cố vấn học tập)`;
      }
      if (btnSave) {
        btnSave.textContent = "💾 Lưu vào Danh bạ K57";
      }
      if (btnCancel) {
        btnCancel.style.display = "none";
      }
    }

    async function renderRosterTable() {
      const tbody = document.getElementById("rosterTableBody");
      if (!tbody) return;
      if (!classRoster || classRoster.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:32px 16px; color:#64748b;">Đang tải danh bạ sinh viên K57 hoặc chưa có dữ liệu...</td></tr>`;
        return;
      }

      // 1. Đồng bộ số liệu on-chain cho từng sinh viên (kèm bộ nhớ đệm cache)
      let paidCount = 0;
      for (const s of classRoster) {
        if (s.wallet && ethers.isAddress(s.wallet)) {
          const key = s.wallet.toLowerCase();
          if (!rosterContribCache.has(key)) {
            if (contract) {
              try {
                const contrib = await contract.studentContributions(s.wallet);
                rosterContribCache.set(key, {
                  isPaid: contrib && contrib > 0n,
                  amountWei: contrib || 0n
                });
              } catch (e) {
                rosterContribCache.set(key, { isPaid: false, amountWei: 0n });
              }
            } else {
              rosterContribCache.set(key, { isPaid: false, amountWei: 0n });
            }
          }
          if (rosterContribCache.get(key).isPaid) {
            paidCount++;
          }
        }
      }

      // 2. Cập nhật 4 thẻ thống kê ở đầu danh bạ
      const totalCount = classRoster.length;
      const bcsCount = classRoster.filter(s => s.role === "bcs").length;
      const studentCount = classRoster.filter(s => s.role !== "bcs").length;

      const elTotal = document.getElementById("rosterStatTotal");
      const elBcs = document.getElementById("rosterStatBcs");
      const elStudents = document.getElementById("rosterStatStudents");
      const elPaid = document.getElementById("rosterStatPaid");

      if (elTotal) elTotal.textContent = `${totalCount} bạn`;
      if (elBcs) elBcs.textContent = `${bcsCount} thành viên`;
      if (elStudents) elStudents.textContent = `${studentCount} bạn`;
      if (elPaid) elPaid.textContent = `${paidCount}/${totalCount} (${Math.round((paidCount / (totalCount || 1)) * 100)}%)`;

      // 3. Lọc danh sách theo từ khóa tìm kiếm và nút filter
      const searchInput = document.getElementById("rosterSearchInput");
      const keyword = (searchInput ? searchInput.value : "").toLowerCase().trim();

      const filtered = classRoster.filter(s => {
        // Lọc theo vai trò & tình trạng nộp
        const cache = s.wallet ? rosterContribCache.get(s.wallet.toLowerCase()) : null;
        const isPaid = cache ? cache.isPaid : false;

        if (currentRosterFilter === "bcs" && s.role !== "bcs") return false;
        if (currentRosterFilter === "student" && s.role === "bcs") return false;
        if (currentRosterFilter === "paid" && !isPaid) return false;
        if (currentRosterFilter === "unpaid" && isPaid) return false;

        // Lọc theo từ khóa (Tên, MSSV, Địa chỉ ví)
        if (keyword) {
          const matchName = (s.name || "").toLowerCase().includes(keyword);
          const matchMssv = (s.mssv || "").toLowerCase().includes(keyword);
          const matchWallet = (s.wallet || "").toLowerCase().includes(keyword);
          if (!matchName && !matchMssv && !matchWallet) return false;
        }

        return true;
      });

      // 4. Cập nhật tóm tắt ở footer
      const footerSum = document.getElementById("rosterFooterSummary");
      if (footerSum) {
        footerSum.innerHTML = `Đang hiển thị <strong>${filtered.length}</strong> / <strong>${totalCount}</strong> sinh viên K57`;
      }

      // 5. Render bảng sinh viên
      if (filtered.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" style="text-align: center; padding: 36px 16px; color: #64748b;">
              <div style="font-size: 2rem; margin-bottom: 8px;">🔍</div>
              <div style="font-weight: 600; color: #0f172a; margin-bottom: 4px;">Không tìm thấy sinh viên phù hợp</div>
              <div style="font-size: 0.8rem;">Thử nhập lại từ khóa khác hoặc chuyển bộ lọc sang "Tất cả".</div>
            </td>
          </tr>
        `;
        return;
      }

      let html = "";
      for (let i = 0; i < filtered.length; i++) {
        const s = filtered[i];
        const isMe = userAddress && s.wallet && userAddress.toLowerCase() === s.wallet.toLowerCase();
        const cache = s.wallet ? rosterContribCache.get(s.wallet.toLowerCase()) : null;
        const isPaid = cache ? cache.isPaid : false;
        const paidAmount = cache && cache.amountWei > 0n ? formatEth(cache.amountWei) : null;

        let statusBadge = "";
        if (isPaid) {
          statusBadge = `<span class="status-pill status-executed" style="font-size: 0.75rem; font-weight: 600; background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0;">✅ Đã nộp (${paidAmount} ETH)</span>`;
        } else {
          statusBadge = `<span class="status-pill" style="font-size: 0.75rem; font-weight: 600; background: #fef2f2; color: #dc2626; border: 1px solid #fecaca;">⏳ Chưa nộp</span>`;
        }

        const roleBadge = (s.role === "bcs")
          ? `<span class="status-pill" style="font-size: 0.75rem; font-weight: 700; background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd;">⭐ ${s.roleTitle || 'Ban cán sự'}</span>`
          : `<span class="status-pill" style="font-size: 0.75rem; font-weight: 600; background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1;">🎓 ${s.roleTitle || 'Sinh viên'}</span>`;

        const canEditStudent = isAdvisor || isBcsMember || (myStudentProfile && myStudentProfile.role === "bcs");
        const actionBtn = canEditStudent
          ? `<button class="btn btn-sm btn-outline" onclick="editRosterStudent('${s.mssv}')" style="padding: 4px 10px; font-size: 0.75rem; border-radius: 6px; cursor: pointer; color: #0284c7; border: 1px solid #bae6fd; background: #f0f9ff; font-weight: 600;" title="Chỉnh sửa thông tin, vai trò hoặc địa chỉ ví của sinh viên này">✏️ Sửa</button>`
          : '<span style="color: #94a3b8; font-size: 0.75rem;">--</span>';

        const avatarGrad = getRosterAvatarGradient(s.mssv || s.name);
        const initials = getInitials(s.name);

        html += `
          <tr class="${isMe ? 'is-me' : ''}">
            <td style="text-align: center; font-weight: 700; color: #64748b; font-size: 0.8rem;">${i + 1}</td>
            <td>
              <div class="roster-student-info">
                <span class="roster-avatar" style="background: ${avatarGrad};">${initials}</span>
                <span class="roster-student-name">
                  ${escapeHtml(s.name)}
                  ${isMe ? '<span class="status-pill status-executed" style="font-size: 0.65rem; padding: 1px 6px; font-weight: 700; background: #22c55e; color: #fff; margin-left: 4px;">Tôi</span>' : ''}
                </span>
              </div>
            </td>
            <td>
              <span class="roster-mssv-badge">${escapeHtml(s.mssv)}</span>
            </td>
            <td>${roleBadge}</td>
            <td>
              <div class="roster-wallet-box">
                <span class="roster-wallet-addr" title="${s.wallet}">${s.wallet}</span>
                <button class="roster-copy-btn" onclick="copyRosterWallet('${s.wallet}', this)" title="Sao chép toàn bộ địa chỉ ví">📋</button>
                <a class="roster-explorer-link" href="https://sepolia.etherscan.io/address/${s.wallet}" target="_blank" rel="noopener noreferrer" title="Mở trên Sepolia Etherscan">↗</a>
              </div>
            </td>
            <td>${statusBadge}</td>
            <td style="text-align: center;">${actionBtn}</td>
          </tr>
        `;
      }

      tbody.innerHTML = html;
    }

    async function saveRosterEntry() {
      const isBcs = isBcsMember || (myStudentProfile && myStudentProfile.role === "bcs");
      if (!isAdvisor && !isBcs) {
        alert("Quyền hạn: Chỉ Ban cán sự hoặc Cố vấn học tập mới có quyền thêm mới hoặc chỉnh sửa danh bạ sinh viên!");
        return;
      }

      const mssv = document.getElementById("formRosterMssv").value.trim();
      const name = document.getElementById("formRosterName").value.trim();
      const wallet = document.getElementById("formRosterWallet").value.trim();
      const roleVal = document.getElementById("formRosterRole").value;
      const [role, roleTitle] = roleVal.split("|");

      if (!mssv || !name || !wallet) {
        alert("Vui lòng nhập đầy đủ MSSV, Họ và tên và Địa chỉ ví!");
        return;
      }
      if (!wallet.startsWith("0x") || wallet.length !== 42) {
        alert("Địa chỉ ví không hợp lệ (phải bắt đầu bằng 0x và đủ 42 ký tự)!");
        return;
      }

      let savedSuccessfully = false;
      try {
        const res = await fetch("http://localhost:8000/api/roster/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            originalMssv: currentEditingMssv,
            mssv,
            name,
            wallet,
            role,
            roleTitle: (role === "bcs") ? "Ban cán sự" : "Sinh viên",
            signerAddress: userAddress || (isAdvisor ? "advisor" : "bcs"),
            isAdvisor: isAdvisor,
            isBcs: isBcs
          })
        });
        const data = await res.json();
        if (data && data.success) {
          alert(data.message || "Lưu thành công vào danh bạ K57!");
          classRoster = data.roster;
          savedSuccessfully = true;
        } else {
          alert("Lỗi từ server: " + (data.error || "Không thể lưu"));
          return;
        }
      } catch (err) {
        console.warn("Máy chủ backend offline, lưu vào bộ nhớ cục bộ:", err);
        let matchIdx = classRoster.findIndex(item => (currentEditingMssv && item.mssv === currentEditingMssv) || item.mssv === mssv);
        if (matchIdx !== -1) {
          classRoster[matchIdx] = { mssv, name, wallet, role, roleTitle: (role === "bcs" ? "Ban cán sự" : "Sinh viên") };
        } else {
          classRoster.push({ mssv, name, wallet, role, roleTitle: (role === "bcs" ? "Ban cán sự" : "Sinh viên") });
        }
        savedSuccessfully = true;
        alert(`Đã lưu thành công sinh viên ${name} (${mssv}) vào bộ nhớ cục bộ!`);
      }

      if (savedSuccessfully) {
        try { localStorage.setItem("kts_class_roster", JSON.stringify(classRoster)); } catch(e){}
        const countBadge = document.getElementById("rosterCountBadge");
        if (countBadge) countBadge.textContent = classRoster.length;
        const sbBadge = document.getElementById("sidebarRosterBadge");
        if (sbBadge) sbBadge.textContent = classRoster.length;
        cancelEditRoster();
        renderRosterTable();
        renderAnnouncementUI(); // Tự động cập nhật sĩ số lớp và tiến độ nộp quỹ khi thêm/sửa sinh viên
        if (userAddress) {
          const s = lookupStudent(userAddress);
          if (s) {
            myStudentProfile = s;
            if (s.role === "bcs") isBcsMember = true;
            updateRoleDisplay(isAdvisor ? "advisor" : (s.role === "bcs" ? "bcs" : "student"), s);
          }
        }
      }
    }

    // Update role display accurately (Sinh viên / Ban cán sự / Cố vấn học tập / Khách vãng lai)
    function updateRoleDisplay(roleType, studentObj = null) {
      const badge = document.getElementById("quickRoleBadge");
      const idEl = document.getElementById("quickStudentIdentity");
      const warnBanner = document.getElementById("guestWarningBanner");
      const adminSec = document.getElementById("rosterAdminSection");

      const sbId = document.getElementById("sidebarUserIdentity");
      const sbRole = document.getElementById("sidebarRoleBadge");
      const sbAddr = document.getElementById("sidebarWalletShort");

      if (!studentObj && userAddress) {
        studentObj = lookupStudent(userAddress);
      }

      // Cập nhật địa chỉ ví vào ngăn kéo sidebar
      if (sbAddr) sbAddr.textContent = userAddress ? shortenAddress(userAddress) : "--";

      if (roleType === "advisor") {
        isAdvisor = true;
        isBcsMember = false;
        if (sbId) sbId.textContent = "Giảng viên phụ trách K57";
        if (sbRole) {
          sbRole.textContent = "🏛️ Cố vấn";
          sbRole.className = "status-pill";
          sbRole.style.background = "var(--advisor-bg, #f3e8ff)";
          sbRole.style.color = "var(--advisor-color, #6d28d9)";
        }
        if (badge) {
          badge.textContent = "🏛️ Cố vấn học tập";
          badge.className = "status-pill";
          badge.style.background = "var(--purple-bg, #f3e8ff)";
          badge.style.color = "#6d28d9";
          badge.style.border = "1px solid #ddd6fe";
        }
        if (idEl) idEl.innerHTML = `<span style="color:#a855f7;">Giảng viên phụ trách K57</span>`;
        if (warnBanner) warnBanner.style.display = "none";
        if (adminSec) adminSec.style.display = "block";
      } else if (roleType === "bcs") {
        isBcsMember = true;
        const nameStr = studentObj ? `${studentObj.name} (${studentObj.mssv})` : "Ban cán sự lớp K57";
        const title = studentObj ? (studentObj.roleTitle || "Ban cán sự") : "Ban cán sự lớp";
        if (sbId) sbId.textContent = nameStr;
        if (sbRole) {
          sbRole.textContent = `⭐ ${title}`;
          sbRole.className = "status-pill";
          sbRole.style.background = "var(--bcs-bg, #dbeafe)";
          sbRole.style.color = "var(--bcs-color, #1d4ed8)";
        }
        if (badge) {
          badge.textContent = `⭐ ${title}`;
          badge.className = "status-pill status-ready";
          badge.style.background = "#dbeafe";
          badge.style.color = "#1d4ed8";
          badge.style.border = "1px solid #bfdbfe";
        }
        if (idEl) {
          idEl.innerHTML = studentObj ? `<strong>${studentObj.name}</strong> (${studentObj.mssv})` : `<span style="color:#93c5fd;">BCS (Chưa liên kết MSSV)</span>`;
        }
        if (warnBanner) warnBanner.style.display = "none";
        // Ban cán sự có quyền mở form quản lý danh bạ
        if (adminSec) adminSec.style.display = "block";
      } else if (studentObj) {
        if (sbId) sbId.textContent = `${studentObj.name} (${studentObj.mssv})`;
        if (sbRole) {
          sbRole.textContent = "🎓 Sinh viên";
          sbRole.className = "status-pill";
          sbRole.style.background = "var(--student-bg, #ecfdf5)";
          sbRole.style.color = "var(--student-color, #047857)";
        }
        if (badge) {
          badge.textContent = "🎓 Sinh viên lớp K57";
          badge.className = "status-pill status-executed";
          badge.style.background = "var(--success-bg, #ecfdf5)";
          badge.style.color = "#047857";
          badge.style.border = "1px solid #a7f3d0";
        }
        if (idEl) idEl.innerHTML = `<strong>${studentObj.name}</strong> (${studentObj.mssv})`;
        if (warnBanner) warnBanner.style.display = "none";
        if (adminSec) adminSec.style.display = "none";
      } else if (userAddress) {
        if (sbId) sbId.textContent = shortenAddress(userAddress);
        if (sbRole) {
          sbRole.textContent = "Khách vãng lai";
          sbRole.className = "status-pill";
          sbRole.style.background = "var(--warning-bg, #fffbeb)";
          sbRole.style.color = "#b45309";
        }
        if (badge) {
          badge.textContent = "⚠️ Khách vãng lai (Chỉ xem)";
          badge.className = "status-pill";
          badge.style.background = "var(--warning-bg, #fffbeb)";
          badge.style.color = "#b45309";
          badge.style.border = "1px solid #fde68a";
        }
        if (idEl) idEl.innerHTML = `<span style="color:#f59e0b;">Chưa có trong danh bạ</span>`;
        if (warnBanner) warnBanner.style.display = "flex";
        if (adminSec) adminSec.style.display = "none";
      } else {
        if (sbId) sbId.textContent = "Chưa kết nối ví";
        if (sbRole) {
          sbRole.textContent = "Chưa xác thực";
          sbRole.className = "status-pill";
          sbRole.style.background = "";
          sbRole.style.color = "";
        }
        if (badge) {
          badge.textContent = "Chưa kết nối ví";
          badge.className = "status-pill status-ready";
          badge.style.background = "";
          badge.style.color = "";
          badge.style.border = "";
        }
        if (idEl) idEl.textContent = "--";
        if (warnBanner) warnBanner.style.display = "none";
        if (adminSec) adminSec.style.display = "none";
      }

      // Phân quyền hiển thị nút Quản trị thông báo: CHỈ HIỆN VỚI BAN CÁN SỰ (HOẶC CỐ VẤN)
      const btnOpenAnn = document.getElementById("btnOpenAnnModal");
      if (btnOpenAnn) {
        if (roleType === "bcs" || roleType === "advisor") {
          btnOpenAnn.style.display = "inline-flex";
        } else {
          btnOpenAnn.style.display = "none";
        }
      }

      // Nút mở modal danh bạ trên thanh hero (hiển thị cho Cố vấn hoặc Ban cán sự)
      const itemRoster = document.getElementById("itemRosterModalBtn");
      if (itemRoster) {
        if (roleType === "bcs" || roleType === "advisor" || isAdvisor || isBcsMember) {
          itemRoster.style.display = "flex";
        } else {
          itemRoster.style.display = "none";
        }
      }
    }

    // Apply contract address & save to localStorage
    function applyContractAddress(address) {
      if (!address || !ethers.isAddress(address)) {
        alert("Địa chỉ hợp đồng không hợp lệ! Vui lòng nhập đúng địa chỉ ví 42 ký tự (bắt đầu bằng 0x).");
        return;
      }
      const prevAddress = CONFIG.contractAddress;
      CONFIG.contractAddress = address;
      localStorage.setItem("kts_class_fund_contract", address);

      // Nếu chuyển sang contract khác, dọn dẹp cache người nộp cũ của contract trước
      if (prevAddress && prevAddress.toLowerCase() !== address.toLowerCase()) {
        localStorage.removeItem("kts_known_depositors");
        logToTerminal(`[Dọn dẹp] Đã chuyển sang contract mới (${shortenAddress(address)}). Làm mới bộ nhớ đệm người nộp.`);
      }

      const quickInp = document.getElementById("quickContractAddress");
      const configInp = document.getElementById("configContractAddress");
      if (quickInp) quickInp.value = address;
      if (configInp) configInp.value = address;

      document.getElementById("textContractConfigStatus").textContent = "Đã cấu hình: " + address;
      document.getElementById("textContractConfigStatus").style.color = "var(--success)";
      document.getElementById("linkEtherscanContract").href = `${CONFIG.blockExplorer}/address/${address}`;

      initContractInstance();
    }

    // Reset to default contract address
    function resetToDefaultContract() {
      if (!CONFIG.defaultContractAddress || !ethers.isAddress(CONFIG.defaultContractAddress)) {
        alert("Chưa có địa chỉ hợp đồng mặc định trong cấu hình.");
        return;
      }
      localStorage.setItem("kts_deployed_contract_default", CONFIG.defaultContractAddress);
      applyContractAddress(CONFIG.defaultContractAddress);
      logToTerminal(`[Khôi phục] Đã đặt lại địa chỉ hợp đồng về mặc định của dự án: ${CONFIG.defaultContractAddress}`);
    }

    // --- 8. CONTRACT INSTANCE & ON-CHAIN DATA ---
    async function initContractInstance() {
      const address = CONFIG.contractAddress;
      if (!address || !ethers.isAddress(address)) return;

      try {
        logToTerminal(`[Hợp đồng] Đang kiểm tra mã bytecode tại: ${shortenAddress(address)}...`);

        // Xác nhận mạng Sepolia và kiểm tra mã bytecode triển khai (Requirement 7)
        if (provider) {
          const code = await provider.getCode(address);
          if (!code || code === "0x" || code === "0x0") {
            const warnMsg = `⚠️ Cảnh báo: Địa chỉ ${address} không có mã bytecode trên Sepolia (ChainID: 11155111). Có thể đây là địa chỉ ví cá nhân (EOA) hoặc hợp đồng chưa được deploy lên mạng Sepolia.`;
            logToTerminal(warnMsg);
            const statusEl = document.getElementById("textContractConfigStatus");
            if (statusEl) {
              statusEl.textContent = "Chưa có bytecode on-chain (Kiểm tra lại Sepolia)";
              statusEl.style.color = "var(--danger)";
            }
            return;
          }
        }

        contract = new ethers.Contract(address, CONTRACT_ABI, signer || provider);
        await refreshContractData();
      } catch (err) {
        logToTerminal(`[Lỗi kết nối contract] ${err.message}`);
        const statusEl = document.getElementById("textContractConfigStatus");
        if (statusEl) {
          statusEl.textContent = "Lỗi kết nối hoặc không tương thích ABI";
          statusEl.style.color = "var(--danger)";
        }
      }
    }

    async function refreshContractData() {
      if (!contract) return;
      try {
        logToTerminal("[Dữ liệu] Đang đồng bộ trạng thái on-chain từ Sepolia...");

        // 1. Read global metrics
        const classFund = await contract.classFundBalance();
        const adminFee = await contract.adminFeePool();
        const spendCount = await contract.spendRequestCount();
        const refundCount = await contract.refundRequestCount();
        const activeBCS = await contract.activeBCSCount();
        const advisorAddr = await contract.advisor();

        document.getElementById("metricClassFund").textContent = formatEth(classFund) + " ETH";
        document.getElementById("metricAdminFee").textContent = formatEth(adminFee) + " ETH";
        document.getElementById("metricSpendCount").textContent = Number(spendCount);
        document.getElementById("metricRefundCount").textContent = Number(refundCount);
        const bcsEl = document.getElementById("metricActiveBCS");
        if (bcsEl) bcsEl.textContent = `${Number(activeBCS)} thành viên`;
        const bcsNote = document.getElementById("metricActiveBCSNote");
        if (bcsNote) bcsNote.textContent = Number(activeBCS) > 0 ? "Đã sẵn sàng biểu quyết (≥51%)" : "Cần Cố vấn kích hoạt (R1)";
        document.getElementById("advisorFeePoolBalance").textContent = formatEth(adminFee) + " ETH";
        document.getElementById("metricClassFundNote").textContent = "Dữ liệu on-chain chính xác";

        // 2. Identify and update user role
        if (userAddress) {
          if (advisorAddr && ethers.isAddress(advisorAddr) && advisorAddr !== "0x0000000000000000000000000000000000000000") {
            isAdvisor = (userAddress.toLowerCase() === advisorAddr.toLowerCase());
          } else {
            isAdvisor = (userAddress.toLowerCase() === "0x36fd4887e9d1eca4ae5062a745cc2c6182b77060".toLowerCase());
          }
          isBcsMember = await contract.isBCSMember(userAddress);
          const student = lookupStudent(userAddress);

          if (isAdvisor) {
            updateRoleDisplay("advisor", student);
            selectRoleView("advisor");
            logToTerminal("[Xác thực] Bạn là Cố vấn học tập. Đã mở ô chi tiết Cố vấn học tập.");
          } else if (isBcsMember) {
            updateRoleDisplay("bcs", student);
            selectRoleView("bcs");
            logToTerminal(`[Xác thực] Bạn là thành viên Ban cán sự${student ? ` (${student.name} - ${student.mssv})` : ''}. Đã mở ô chi tiết Ban cán sự.`);
          } else if (student) {
            updateRoleDisplay("student", student);
            selectRoleView("student");
            logToTerminal(`[Xác thực] Chào bạn ${student.name} (MSSV: ${student.mssv}) - Sinh viên lớp K57.`);
          } else {
            updateRoleDisplay("guest", null);
            const sbId = document.getElementById("sidebarUserIdentity");
            const sbRole = document.getElementById("sidebarRoleBadge");
            const sbAddr = document.getElementById("sidebarWalletShort");
            if (sbId) sbId.textContent = "Chưa kết nối ví";
            if (sbRole) { sbRole.textContent = "Chưa kết nối"; sbRole.className = "status-pill status-ready"; sbRole.style.background = ""; sbRole.style.color = ""; }
            if (sbAddr) sbAddr.textContent = "--";
            selectRoleView("student");
            logToTerminal(`[Cảnh báo] Địa chỉ ví ${shortenAddress(userAddress)} chưa thuộc danh bạ sinh viên K57. Chế độ khách vãng lai.`);
          }

          // 3. User personal contribution
          const myContrib = await contract.studentContributions(userAddress);
          const myPending = await contract.pendingStudentRefundAmount(userAddress);
          const myAvail = await contract.getStudentAvailableContribution(userAddress);

          document.getElementById("myTotalContribution").textContent = formatEth(myContrib) + " ETH";
          document.getElementById("myPendingRefund").textContent = formatEth(myPending) + " ETH";
          document.getElementById("myAvailableRefund").textContent = formatEth(myAvail) + " ETH";
        }

        // 4. Load Requests Data & Cash Flow Ledger
        await loadSpendRequests(Number(spendCount), Number(activeBCS));
        await loadRefundRequests(Number(refundCount), Number(activeBCS));
        await loadCashFlowLedger(Number(spendCount), Number(refundCount), Number(activeBCS), classFund, adminFee);
        await syncDepositorsData(classFund, adminFee);

        logToTerminal("[Dữ liệu] Hoàn tất đồng bộ dữ liệu hợp đồng và toàn bộ flow dòng tiền.");
      } catch (err) {
        logToTerminal(`[Lỗi đọc hợp đồng] ${err.shortMessage || err.message}`);
      }
    }

    // Load Spend Requests
    async function loadSpendRequests(totalCount, activeBcsCount) {
      const bcsTableBody = document.getElementById("bcsSpendTableBody");
      if (!bcsTableBody) return;

      if (totalCount === 0) {
        bcsTableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:18px; color:var(--text-muted);">Hiện chưa có đề nghị chi tiền nào trong hợp đồng.</td></tr>`;
        return;
      }

      let rowsHtml = "";
      for (let i = 1; i <= totalCount; i++) {
        try {
          const req = await contract.getSpendRequest(i);
          const reqId = Number(req[0]);
          const recipient = req[1];
          const amount = formatEth(req[2]);
          const desc = req[3];
          const yesVotes = Number(req[6]);
          const status = Number(req[8]);

          const pct = activeBcsCount > 0 ? ((yesVotes / activeBcsCount) * 100).toFixed(0) : 0;
          const statusBadge = getStatusBadge(status);

          let voteActionHtml = "";
          let executeActionHtml = "";

          if (status === 0) { // Pending
            voteActionHtml = `
              <button class="btn btn-sm btn-primary" onclick="voteSpend(${reqId}, true)">Đồng ý</button>
              <button class="btn btn-sm btn-danger" onclick="voteSpend(${reqId}, false)">Bác bỏ</button>
            `;
            executeActionHtml = `<span style="font-size:0.78rem; color:var(--text-light);">Cần &ge; 51% đồng ý</span>`;
          } else if (status === 1) { // Ready
            voteActionHtml = `<span style="font-size:0.8rem; color:var(--brand-blue); font-weight:600;">Đã đủ điều kiện</span>`;
            executeActionHtml = `<button class="btn btn-sm btn-success" onclick="executeSpend(${reqId})">Giải ngân</button>`;
          } else {
            voteActionHtml = `-`;
            executeActionHtml = `-`;
          }

          const recStudent = lookupStudent(recipient);
          const recLabel = recStudent ? `<span title="${recipient}"><strong>${recStudent.name}</strong> (${recStudent.mssv})</span>` : `<span title="${recipient}" style="font-family:monospace;">${shortenAddress(recipient)}</span>`;

          rowsHtml += `
            <tr>
              <td><strong>#${reqId}</strong></td>
              <td>${recLabel}</td>
              <td><strong>${amount} ETH</strong></td>
              <td>${desc}</td>
              <td>${yesVotes}/${activeBcsCount} (${pct}%)</td>
              <td>${statusBadge}</td>
              <td>${voteActionHtml}</td>
              <td>${executeActionHtml}</td>
            </tr>
          `;
        } catch (e) {
          console.error("Lỗi đọc đề nghị chi", i, e);
        }
      }
      bcsTableBody.innerHTML = rowsHtml;
    }

    // Load Refund Requests
    async function loadRefundRequests(totalCount, activeBcsCount) {
      const bcsRefundTable = document.getElementById("bcsRefundTableBody");
      const studentRefundTable = document.getElementById("studentRefundTableBody");

      if (totalCount === 0) {
        if (bcsRefundTable) bcsRefundTable.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:18px; color:var(--text-muted);">Hiện chưa có yêu cầu hoàn tiền nào từ sinh viên.</td></tr>`;
        if (studentRefundTable) studentRefundTable.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:18px; color:var(--text-muted);">Bạn chưa tạo yêu cầu hoàn tiền nào.</td></tr>`;
        return;
      }

      let bcsRows = "";
      let studentRows = "";

      for (let i = 1; i <= totalCount; i++) {
        try {
          const req = await contract.getRefundRequest(i);
          const refId = Number(req[0]);
          const applicant = req[1];
          const amount = formatEth(req[2]);
          const reason = req[3];
          const yesVotes = Number(req[5]);
          const status = Number(req[7]);

          const pct = activeBcsCount > 0 ? ((yesVotes / activeBcsCount) * 100).toFixed(0) : 0;
          const statusBadge = getStatusBadge(status);

          // For BCS table
          let bcsVoteHtml = "";
          let bcsExecHtml = "";
          if (status === 0) {
            bcsVoteHtml = `
              <button class="btn btn-sm btn-primary" onclick="voteRefund(${refId}, true)">Đồng ý duyệt</button>
              <button class="btn btn-sm btn-danger" onclick="voteRefund(${refId}, false)">Bác bỏ</button>
            `;
            bcsExecHtml = `<span style="font-size:0.78rem; color:var(--text-light);">Cần &ge; 51% đồng ý</span>`;
          } else if (status === 1) {
            bcsVoteHtml = `<span style="font-size:0.8rem; color:var(--brand-blue); font-weight:600;">Đã thông qua</span>`;
            bcsExecHtml = `<button class="btn btn-sm btn-success" onclick="executeRefund(${refId})">Hoàn tiền</button>`;
          } else {
            bcsVoteHtml = `-`;
            bcsExecHtml = `-`;
          }

          const appStudent = lookupStudent(applicant);
          const appLabel = appStudent ? `<span title="${applicant}"><strong>${appStudent.name}</strong> (${appStudent.mssv})</span>` : `<span style="font-family:monospace;">${shortenAddress(applicant)}</span>`;

          bcsRows += `
            <tr>
              <td><strong>#${refId}</strong></td>
              <td>${appLabel}</td>
              <td><strong>${amount} ETH</strong></td>
              <td>${reason}</td>
              <td>${yesVotes}/${activeBcsCount} (${pct}%)</td>
              <td>${statusBadge}</td>
              <td>${bcsVoteHtml}</td>
              <td>${bcsExecHtml}</td>
            </tr>
          `;

          // For Student's table
          if (userAddress && applicant.toLowerCase() === userAddress.toLowerCase()) {
            let studentExecBtn = (status === 1) ? `<button class="btn btn-sm btn-success" onclick="executeRefund(${refId})">Nhận tiền hoàn</button>` : `-`;
            studentRows += `
              <tr>
                <td><strong>#${refId}</strong></td>
                <td><strong>${amount} ETH</strong></td>
                <td>${reason}</td>
                <td>${yesVotes}/${activeBcsCount} (${pct}%)</td>
                <td>${statusBadge}</td>
                <td>${studentExecBtn}</td>
              </tr>
            `;
          }
        } catch (e) {
          console.error("Lỗi đọc yêu cầu hoàn tiền", i, e);
        }
      }

      if (bcsRefundTable) bcsRefundTable.innerHTML = bcsRows || `<tr><td colspan="8" style="text-align:center;">Không có dữ liệu</td></tr>`;
      if (studentRefundTable) studentRefundTable.innerHTML = studentRows || `<tr><td colspan="6" style="text-align:center; padding:18px; color:var(--text-muted);">Tài khoản hiện tại chưa tạo yêu cầu hoàn tiền nào.</td></tr>`;
    }

    // --- 9. CASH FLOW LEDGER & FLOW TRACKER ---
    async function loadCashFlowLedger(spendCount, refundCount, activeBcsCount, classFundWei, adminFeeWei) {
      const tableBody = document.getElementById("flowLedgerTableBody");
      const flowBalClass = document.getElementById("flowBalClassFund");
      const flowBalRes = document.getElementById("flowBalReserved");
      const flowBalFee = document.getElementById("flowBalAdminFee");
      const flowBalExec = document.getElementById("flowBalExecutedSpend");
      const flowBalExecCount = document.getElementById("flowBalExecutedCount");
      const linkEtherscan = document.getElementById("flowLinkEtherscan");

      if (flowBalClass) flowBalClass.textContent = formatEth(classFundWei) + " ETH";
      if (flowBalFee) flowBalFee.textContent = formatEth(adminFeeWei) + " ETH";
      if (linkEtherscan && CONFIG.contractAddress) {
        linkEtherscan.href = `${CONFIG.blockExplorer}/address/${CONFIG.contractAddress}`;
      }

      allFlowItems = [];
      let totalExecutedSpendWei = 0n;
      let executedSpendCount = 0;
      let totalReservedWei = 0n;

      // 1. Fetch reserved amounts if available
      try {
        const resSpend = await contract.reservedSpendAmount();
        const resRefund = await contract.reservedRefundAmount();
        totalReservedWei = (resSpend || 0n) + (resRefund || 0n);
      } catch (e) {
        console.warn("Could not read reserved amounts", e);
      }
      if (flowBalRes) flowBalRes.textContent = formatEth(totalReservedWei) + " ETH";

      // 2. Collect all Spend Requests into ledger
      for (let i = 1; i <= spendCount; i++) {
        try {
          const req = await contract.getSpendRequest(i);
          const reqId = Number(req[0]);
          const recipient = req[1];
          const rawAmount = req[2];
          const desc = req[3];
          const creator = req[4];
          const createdAt = Number(req[5]);
          const yesVotes = Number(req[6]);
          const status = Number(req[8]);

          if (status === 2) { // Executed
            totalExecutedSpendWei += rawAmount;
            executedSpendCount++;
          }

          const pct = activeBcsCount > 0 ? ((yesVotes / activeBcsCount) * 100).toFixed(0) : 0;
          const canViewIdentity = isAdvisor || isBcsMember;
          const recStudent = canViewIdentity ? lookupStudent(recipient) : null;
          const creStudent = canViewIdentity ? lookupStudent(creator) : null;
          const recText = recStudent ? `${recStudent.name} (${recStudent.mssv})` : shortenAddress(recipient);
          const creText = creStudent ? `${creStudent.name} (${creStudent.mssv})` : shortenAddress(creator);

          allFlowItems.push({
            category: "spend",
            id: `SP-${reqId}`,
            numId: reqId,
            flowType: "📤 Chi tiêu",
            badgeClass: "flow-badge-spend",
            amountEth: formatEth(rawAmount),
            party: `Nhận: ${recText} (Tạo: ${creText})`,
            desc: desc,
            votesText: `${yesVotes}/${activeBcsCount} (${pct}%)`,
            statusNum: status,
            statusBadge: getStatusBadge(status),
            createdAt: createdAt ? new Date(createdAt * 1000).toLocaleDateString("vi-VN") : "Gần đây"
          });
        } catch (e) {
          console.error("Error reading spend for ledger", i, e);
        }
      }

      // 3. Collect all Refund Requests into ledger
      for (let i = 1; i <= refundCount; i++) {
        try {
          const req = await contract.getRefundRequest(i);
          const refId = Number(req[0]);
          const applicant = req[1];
          const rawAmount = req[2];
          const reason = req[3];
          const createdAt = Number(req[4]);
          const yesVotes = Number(req[5]);
          const status = Number(req[7]);

          const pct = activeBcsCount > 0 ? ((yesVotes / activeBcsCount) * 100).toFixed(0) : 0;
          const canViewIdentity = isAdvisor || isBcsMember;
          const appStudent = canViewIdentity ? lookupStudent(applicant) : null;
          const appText = appStudent ? `${appStudent.name} (${appStudent.mssv})` : shortenAddress(applicant);

          allFlowItems.push({
            category: "refund",
            id: `RF-${refId}`,
            numId: refId,
            flowType: "🔄 Hoàn tiền",
            badgeClass: "flow-badge-refund",
            amountEth: formatEth(rawAmount),
            party: `SV: ${appText}`,
            desc: reason,
            votesText: `${yesVotes}/${activeBcsCount} (${pct}%)`,
            statusNum: status,
            statusBadge: getStatusBadge(status),
            createdAt: createdAt ? new Date(createdAt * 1000).toLocaleDateString("vi-VN") : "Gần đây"
          });
        } catch (e) {
          console.error("Error reading refund for ledger", i, e);
        }
      }

      if (flowBalExec) flowBalExec.textContent = formatEth(totalExecutedSpendWei) + " ETH";
      if (flowBalExecCount) flowBalExecCount.textContent = `${executedSpendCount} khoản chi đã giải ngân`;

      renderFlowLedgerTable(allFlowItems);
    }

    function renderFlowLedgerTable(items) {
      const tableBody = document.getElementById("flowLedgerTableBody");
      if (!tableBody) return;

      if (!items || items.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:24px; color:var(--text-muted);">Hiện chưa có đề xuất chi tiêu hoặc yêu cầu hoàn tiền nào trong hợp đồng.</td></tr>`;
        return;
      }

      let rowsHtml = "";
      items.forEach(item => {
        const isSpend = item.category === "spend";
        const sign = isSpend ? "- " : "~ ";
        const amountColor = isSpend ? "#ef4444" : "#ea580c";

        rowsHtml += `
          <tr>
            <td><span class="flow-step-badge ${item.badgeClass}">${item.flowType}</span></td>
            <td><strong>#${item.id}</strong></td>
            <td><strong style="color:${amountColor};">${sign}${item.amountEth} ETH</strong></td>
            <td><span style="font-family:monospace; font-size:0.85rem;">${item.party}</span></td>
            <td>${item.desc}</td>
            <td>${item.votesText}</td>
            <td>${item.statusBadge}</td>
            <td>
              <a href="${CONFIG.blockExplorer}/address/${CONFIG.contractAddress}" target="_blank" style="font-size:0.8rem; color:var(--brand-blue); text-decoration:underline;">
                Xem Tx ↗
              </a>
            </td>
          </tr>
        `;
      });

      tableBody.innerHTML = rowsHtml;
    }

    function filterFlowLedger(filterType, btnEl) {
      const buttons = document.querySelectorAll("#flowFilterGroup .flow-filter-btn");
      buttons.forEach(b => b.classList.remove("active"));
      if (btnEl) btnEl.classList.add("active");

      if (filterType === "all") {
        renderFlowLedgerTable(allFlowItems);
      } else if (filterType === "spend") {
        const filtered = allFlowItems.filter(item => item.category === "spend");
        renderFlowLedgerTable(filtered);
      } else if (filterType === "refund") {
        const filtered = allFlowItems.filter(item => item.category === "refund");
        renderFlowLedgerTable(filtered);
      } else if (filterType === "executed") {
        const filtered = allFlowItems.filter(item => item.statusNum === 2); // Executed
        renderFlowLedgerTable(filtered);
      } else if (filterType === "pending") {
        const filtered = allFlowItems.filter(item => item.statusNum === 0); // Pending
        renderFlowLedgerTable(filtered);
      }
    }

    // --- 9. TRANSACTIONS VIA SIGNER ---

    // Nộp tiền vào quỹ
    async function doDeposit() {
      if (!signer) {
        alert("Bạn chưa kết nối ví MetaMask! Vui lòng bấm nút 'Kết nối MetaMask' ở thanh menu trên cùng.");
        return;
      }
      if (!contract) {
        promptContractConfig("nộp tiền vào quỹ");
        return;
      }

      const amountStr = document.getElementById("inputDepositAmount").value.trim();
      if (!amountStr || parseFloat(amountStr) <= 0) return alert("Vui lòng nhập số ETH đóng góp lớn hơn 0!");

      try {
        logToTerminal(`[Đóng góp] Đang chuẩn bị nộp ${amountStr} ETH vào quỹ lớp...`);
        const valueWei = ethers.parseEther(amountStr);
        const tx = await contract.deposit({ value: valueWei });
        logToTerminal(`[Đang xử lý] Mã giao dịch: ${tx.hash}. Đang chờ xác nhận từ blockchain...`);
        logToTerminal(`[Thành công] Đã nộp thành công ${amountStr} ETH vào Quỹ lớp!`);
        alert(`Đóng góp tiền vào quỹ thành công! Mã giao dịch: ${tx.hash}`);
        document.getElementById("inputDepositAmount").value = "";
        try {
          const known = JSON.parse(localStorage.getItem("kts_known_depositors") || "[]");
          if (userAddress && !known.includes(userAddress.toLowerCase())) {
            known.push(userAddress.toLowerCase());
            localStorage.setItem("kts_known_depositors", JSON.stringify(known));
          }
        } catch (e) { }
        await refreshContractData();
      } catch (err) {
        logToTerminal(`[Lỗi nộp quỹ] ${err.shortMessage || err.message}`);
        alert("Giao dịch nộp tiền thất bại: " + (err.shortMessage || err.message));
      }
    }

    // Gửi yêu cầu hoàn tiền
    async function doCreateRefund() {
      if (!signer) {
        alert("Bạn chưa kết nối ví MetaMask! Vui lòng bấm nút 'Kết nối MetaMask' ở thanh menu trên cùng.");
        return;
      }
      if (!contract) {
        promptContractConfig("gửi yêu cầu hoàn tiền");
        return;
      }

      const amountStr = document.getElementById("inputRefundAmount").value.trim();
      const reason = document.getElementById("inputRefundReason").value.trim();
      if (!amountStr || parseFloat(amountStr) <= 0) return alert("Vui lòng nhập số ETH muốn xin hoàn lại hợp lệ!");
      if (!reason) return alert("Vui lòng nhập rõ lý do chuyển nhầm tiền!");

      try {
        logToTerminal(`[Yêu cầu hoàn tiền] Đang gửi yêu cầu xin hoàn ${amountStr} ETH...`);
        const valueWei = ethers.parseEther(amountStr);
        const tx = await contract.createRefundRequest(valueWei, reason);
        logToTerminal(`[Đang xử lý] Mã giao dịch: ${tx.hash}. Chờ xác nhận...`);
        await tx.wait();
        logToTerminal(`[Thành công] Đã gửi yêu cầu hoàn tiền thành công! Đang chờ Ban cán sự xem xét.`);
        alert("Yêu cầu hoàn tiền đã được gửi thành công! Mã giao dịch: " + tx.hash);
        document.getElementById("inputRefundAmount").value = "";
        document.getElementById("inputRefundReason").value = "";
        await refreshContractData();
      } catch (err) {
        logToTerminal(`[Lỗi gửi yêu cầu hoàn tiền] ${err.shortMessage || err.message}`);
        alert("Không thể gửi yêu cầu hoàn tiền: " + (err.shortMessage || err.message));
      }
    }

    // Ban cán sự biểu quyết duyệt hoàn tiền
    async function voteRefund(refundId, support) {
      if (!signer) {
        alert("Bạn chưa kết nối ví MetaMask!");
        return;
      }
      if (!contract) {
        promptContractConfig("biểu quyết duyệt hoàn tiền");
        return;
      }

      try {
        logToTerminal(`[Biểu quyết hoàn tiền] Đang bỏ phiếu ${support ? 'ĐỒNG Ý' : 'KHÔNG ĐỒNG Ý'} cho Yêu cầu #${refundId}...`);
        const tx = await contract.voteRefundRequest(refundId, support);
        await tx.wait();
        logToTerminal(`[Thành công] Đã bỏ phiếu thành công cho Yêu cầu hoàn tiền #${refundId}!`);
        await refreshContractData();
      } catch (err) {
        logToTerminal(`[Lỗi bỏ phiếu hoàn tiền] ${err.shortMessage || err.message}`);
        alert("Bỏ phiếu thất bại: " + (err.shortMessage || err.message));
      }
    }

    // Thực hiện hoàn tiền về ví sinh viên
    async function executeRefund(refundId) {
      if (!signer) {
        alert("Bạn chưa kết nối ví MetaMask!");
        return;
      }
      if (!contract) {
        promptContractConfig("thực hiện hoàn tiền");
        return;
      }

      try {
        logToTerminal(`[Hoàn tiền] Đang thực hiện chuyển tiền hoàn cho Yêu cầu #${refundId}...`);
        const tx = await contract.executeRefundRequest(refundId);
        await tx.wait();
        logToTerminal(`[Thành công] Tiền hoàn đã được chuyển về ví của sinh viên! Mã giao dịch: ${tx.hash}`);
        alert("Hoàn tiền thành công về ví sinh viên! Mã giao dịch: " + tx.hash);
        await refreshContractData();
      } catch (err) {
        logToTerminal(`[Lỗi hoàn tiền] ${err.shortMessage || err.message}`);
        alert("Thực hiện hoàn tiền thất bại: " + (err.shortMessage || err.message));
      }
    }

    // Tạo đề xuất chi tiêu
    async function doCreateSpend() {
      if (!signer) {
        alert("Bạn chưa kết nối ví MetaMask!");
        return;
      }
      if (!contract) {
        promptContractConfig("tạo đề nghị chi tiền");
        return;
      }

      const recipient = document.getElementById("inputSpendRecipient").value.trim();
      const amountStr = document.getElementById("inputSpendAmount").value.trim();
      const desc = document.getElementById("inputSpendDesc").value.trim();

      if (!recipient || !ethers.isAddress(recipient)) return alert("Vui lòng nhập địa chỉ ví người nhận tiền hợp lệ!");
      if (!amountStr || parseFloat(amountStr) <= 0) return alert("Vui lòng nhập số ETH đề nghị chi hợp lệ!");
      if (!desc) return alert("Vui lòng nhập nội dung chi tiêu!");

      try {
        logToTerminal(`[Đề nghị chi] Đang tạo đề nghị chi ${amountStr} ETH cho ${shortenAddress(recipient)}...`);
        const amountWei = ethers.parseEther(amountStr);
        const tx = await contract.createSpendRequest(recipient, amountWei, desc);
        await tx.wait();
        logToTerminal(`[Thành công] Đã tạo đề nghị chi tiền mới! Khoản tiền đã được tạm giữ an toàn.`);
        alert("Tạo đề nghị chi tiền thành công! Mã giao dịch: " + tx.hash);
        document.getElementById("inputSpendRecipient").value = "";
        document.getElementById("inputSpendAmount").value = "";
        document.getElementById("inputSpendDesc").value = "";
        await refreshContractData();
      } catch (err) {
        logToTerminal(`[Lỗi tạo đề nghị chi] ${err.shortMessage || err.message}`);
        alert("Tạo đề nghị chi thất bại: " + (err.shortMessage || err.message));
      }
    }

    // Ban cán sự biểu quyết đề xuất chi
    async function voteSpend(requestId, support) {
      if (!signer) {
        alert("Bạn chưa kết nối ví MetaMask!");
        return;
      }
      if (!contract) {
        promptContractConfig("bỏ phiếu đề nghị chi");
        return;
      }

      try {
        logToTerminal(`[Biểu quyết chi] Đang bỏ phiếu ${support ? 'ĐỒNG Ý' : 'KHÔNG ĐỒNG Ý'} cho Đề xuất #${requestId}...`);
        const tx = await contract.voteSpendRequest(requestId, support);
        await tx.wait();
        logToTerminal(`[Thành công] Đã ghi nhận phiếu biểu quyết cho Đề xuất #${requestId}!`);
        await refreshContractData();
      } catch (err) {
        logToTerminal(`[Lỗi bỏ phiếu chi] ${err.shortMessage || err.message}`);
        alert("Bỏ phiếu thất bại: " + (err.shortMessage || err.message));
      }
    }

    // Thực hiện giải ngân đề xuất chi
    async function executeSpend(requestId) {
      if (!signer) {
        alert("Bạn chưa kết nối ví MetaMask!");
        return;
      }
      if (!contract) {
        promptContractConfig("thực hiện giải ngân");
        return;
      }

      try {
        logToTerminal(`[Giải ngân chi tiêu] Đang thực hiện chuyển tiền cho Đề xuất #${requestId}...`);
        const tx = await contract.executeSpendRequest(requestId);
        await tx.wait();
        logToTerminal(`[Thành công] Đã giải ngân thành công! Tiền đã chuyển đến người nhận. Mã giao dịch: ${tx.hash}`);
        alert("Giải ngân thành công! Mã giao dịch: " + tx.hash);
        await refreshContractData();
      } catch (err) {
        logToTerminal(`[Lỗi giải ngân] ${err.shortMessage || err.message}`);
        alert("Giải ngân thất bại: " + (err.shortMessage || err.message));
      }
    }

    // Cố vấn học tập cập nhật nhân sự Ban cán sự
    async function doSetBCS() {
      if (!signer) {
        alert("Bạn chưa kết nối ví MetaMask!");
        return;
      }
      if (!contract) {
        promptContractConfig("cập nhật nhân sự Ban cán sự");
        return;
      }

      const memberAddr = document.getElementById("inputBcsAddress").value.trim();
      const statusVal = (document.getElementById("selectBcsStatus").value === "true");

      if (!memberAddr || !ethers.isAddress(memberAddr)) return alert("Vui lòng nhập địa chỉ ví hợp lệ!");

      try {
        logToTerminal(`[Quản trị Cố vấn] Đang cập nhật quyền Ban cán sự cho ${shortenAddress(memberAddr)} -> ${statusVal ? 'Kích hoạt' : 'Thu hồi'}...`);
        const tx = await contract.setBCSMember(memberAddr, statusVal);
        await tx.wait();
        logToTerminal(`[Thành công] Đã cập nhật thành công nhân sự Ban cán sự! Mã giao dịch: ${tx.hash}`);
        alert("Cập nhật Ban cán sự thành công! Mã giao dịch: " + tx.hash);
        document.getElementById("inputBcsAddress").value = "";
        await refreshContractData();
      } catch (err) {
        logToTerminal(`[Lỗi cập nhật BCS] ${err.shortMessage || err.message}`);
        alert("Cập nhật BCS thất bại: " + (err.shortMessage || err.message));
      }
    }

    // Cố vấn học tập rút quỹ phí vận hành bù gas
    async function doWithdrawFee() {
      if (!signer) {
        alert("Bạn chưa kết nối ví MetaMask!");
        return;
      }
      if (!contract) {
        promptContractConfig("rút quỹ phí vận hành");
        return;
      }

      const amountStr = document.getElementById("inputWithdrawFeeAmount").value.trim();
      if (!amountStr || parseFloat(amountStr) <= 0) return alert("Vui lòng nhập số ETH muốn rút hợp lệ!");

      try {
        logToTerminal(`[Rút phí Cố vấn] Đang rút ${amountStr} ETH từ quỹ phí vận hành về ví Cố vấn...`);
        const amountWei = ethers.parseEther(amountStr);
        const tx = await contract.withdrawAdminFee(amountWei);
        await tx.wait();
        logToTerminal(`[Thành công] Đã rút thành công phí vận hành bù đắp gas! Mã giao dịch: ${tx.hash}`);
        alert("Rút phí vận hành thành công! Mã giao dịch: " + tx.hash);
        document.getElementById("inputWithdrawFeeAmount").value = "";
        await refreshContractData();
      } catch (err) {
        logToTerminal(`[Lỗi rút phí vận hành] ${err.shortMessage || err.message}`);
        alert("Rút phí thất bại: " + (err.shortMessage || err.message));
      }
    }

    // --- 10. SETUP EVENT LISTENERS ---
    window.addEventListener("DOMContentLoaded", () => {
      // Setup FAQ
      renderFaq(FAQ_DATA);
      const searchBox = document.getElementById("faqSearchInput");
      if (searchBox) {
        searchBox.addEventListener("input", (e) => {
          const keyword = e.target.value.toLowerCase().trim();
          // Filter via applyFaqFilter
        applyFaqFilter(); return;
        const filtered = FAQ_DATA.filter(item => item.q.toLowerCase().includes(keyword) || item.a.toLowerCase().includes(keyword));
          renderFaq(filtered);
        });
      }

      // Setup Calculator
      setupCalculator();

      // Mobile nav toggle
      // Mobile & Sidebar navigation toggle
      const btnToggle = document.getElementById("btnToggleNav");
      const sidebarEl = document.getElementById("appSidebar");
      const backdropEl = document.getElementById("sidebarBackdrop");
      if (btnToggle && sidebarEl) {
        btnToggle.addEventListener("click", () => {
          sidebarEl.classList.toggle("show");
          if (backdropEl) backdropEl.classList.toggle("show");
        });
      }
      if (backdropEl && sidebarEl) {
        backdropEl.addEventListener("click", () => {
          sidebarEl.classList.remove("show");
          backdropEl.classList.remove("show");
        });
      }
      // Close sidebar when clicking links on mobile
      document.querySelectorAll(".sidebar-link").forEach(link => {
        link.addEventListener("click", () => {
          if (window.innerWidth <= 1024 && sidebarEl) {
            sidebarEl.classList.remove("show");
            if (backdropEl) backdropEl.classList.remove("show");
          }
        });
      });

      // Action buttons
      document.getElementById("btnConnectWallet").addEventListener("click", connectWallet);
      document.getElementById("btnDepositAction").addEventListener("click", doDeposit);
      document.getElementById("btnCreateRefundAction").addEventListener("click", doCreateRefund);
      document.getElementById("btnCreateSpendAction").addEventListener("click", doCreateSpend);
      document.getElementById("btnSetBcsAction").addEventListener("click", doSetBCS);
      document.getElementById("btnWithdrawFeeAction").addEventListener("click", doWithdrawFee);

      // Contract apply buttons
      document.getElementById("btnSaveQuickContract").addEventListener("click", () => {
        const val = document.getElementById("quickContractAddress").value.trim();
        applyContractAddress(val);
      });
      document.getElementById("btnApplyContractAddress").addEventListener("click", () => {
        const val = document.getElementById("configContractAddress").value.trim();
        applyContractAddress(val);
      });

      // Init Web3 Provider
      initWeb3();

      // Init Class Announcement System
      initAnnouncementSystem();

      // Init Class Roster & Student Verification
      loadClassRoster();

      // Init AI Chatbot
      initAIChatbot();

      // Lắng nghe phím Escape để đóng nhanh modal danh bạ hoặc thông báo
      window.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
          const rosterModal = document.getElementById("rosterModal");
          if (rosterModal && (rosterModal.classList.contains("open") || rosterModal.classList.contains("show"))) {
            closeRosterModal();
          }
          const annModal = document.getElementById("announcementModal");
          if (annModal && (annModal.classList.contains("open") || annModal.classList.contains("show"))) {
            closeAnnModal();
          }
        }
      });
    });

    window.addEventListener('ethereum#initialized', () => {
      initWeb3();
    }, { once: true });

    // ============================================================
    // AI ASSISTANT CHATBOT LOGIC
    // ============================================================
    const AI_BACKEND_URL = "http://localhost:8000";
    let isAIOpen = false;

    function initAIChatbot() {
      const fabBtn = document.getElementById("aiFabToggle");
      const drawer = document.getElementById("aiChatDrawer");
      const closeBtn = document.getElementById("aiBtnClose");
      const sendBtn = document.getElementById("aiBtnSend");
      const input = document.getElementById("aiUserInput");

      if (!fabBtn || !drawer) return;

      fabBtn.addEventListener("click", () => {
        isAIOpen = !isAIOpen;
        drawer.classList.toggle("open", isAIOpen);
        if (isAIOpen) {
          checkAIStatus();
          input.focus();
        }
      });

      closeBtn.addEventListener("click", () => {
        isAIOpen = false;
        drawer.classList.remove("open");
      });

      sendBtn.addEventListener("click", () => handleUserSend());
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          handleUserSend();
        }
      });

      // Kiểm tra trạng thái backend ngay khi nạp trang
      checkAIStatus();
    }

    async function checkAIStatus() {
      const indicator = document.getElementById("aiStatusIndicator");
      const statusText = document.getElementById("aiStatusText");
      if (!indicator || !statusText) return;

      try {
        const resp = await fetch(`${AI_BACKEND_URL}/api/status`, { method: "GET" });
        if (resp.ok) {
          const data = await resp.json();
          indicator.className = "ai-status-indicator online";
          statusText.textContent = data.is_configured ? "Backend Python sẵn sàng" : "Thiếu GEMINI_API_KEY";
          statusText.style.color = data.is_configured ? "#10b981" : "#f59e0b";
        } else {
          throw new Error("Backend response not ok");
        }
      } catch (err) {
        indicator.className = "ai-status-indicator offline";
        statusText.textContent = "Chưa kết nối Backend (Port 8000)";
        statusText.style.color = "#ef4444";
      }
    }

    function appendAIMessage(sender, htmlContent) {
      const body = document.getElementById("aiChatBody");
      if (!body) return;

      const msgDiv = document.createElement("div");
      msgDiv.className = `ai-msg ai-msg-${sender}`;
      msgDiv.innerHTML = htmlContent;
      body.appendChild(msgDiv);
      body.scrollTop = body.scrollHeight;
      return msgDiv;
    }

    function showTypingIndicator() {
      const body = document.getElementById("aiChatBody");
      if (!body) return null;

      const indicator = document.createElement("div");
      indicator.className = "ai-msg ai-msg-bot ai-typing-indicator";
      indicator.id = "aiTypingIndicator";
      indicator.innerHTML = `
        <span class="ai-typing-dot"></span>
        <span class="ai-typing-dot"></span>
        <span class="ai-typing-dot"></span>
        <span style="font-size:0.75rem; color:#64748b; margin-left:6px;">AI đang suy nghĩ...</span>
      `;
      body.appendChild(indicator);
      body.scrollTop = body.scrollHeight;
      return indicator;
    }

    function removeTypingIndicator() {
      const el = document.getElementById("aiTypingIndicator");
      if (el) el.remove();
    }

    function askAIPrompt(text) {
      const input = document.getElementById("aiUserInput");
      if (input) {
        input.value = text;
        handleUserSend();
      }
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.innerText = text;
      return div.innerHTML;
    }

    function formatAIReply(text) {
      let formatted = escapeHtml(text);
      formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
      formatted = formatted.replace(/`([^`]+)`/g, '<code style="background:#f1f5f9; color:#0f172a; padding:2px 6px; border-radius:4px; font-family:monospace; font-size:0.85em; border:1px solid #cbd5e1;">$1</code>');
      formatted = formatted.replace(/^\*\s+(.*)$/gm, '&bull; $1');
      formatted = formatted.replace(/\n\n/g, '<br><br>');
      formatted = formatted.replace(/\n/g, '<br>');
      return formatted;
    }

    // ============================================================
    // HỆ THỐNG THÔNG BÁO NỘP QUỸ LỚP (CLASS ANNOUNCEMENT SYSTEM)
    // ============================================================
    const DEFAULT_ANNOUNCEMENT = {
      title: "Kêu gọi nộp Quỹ Lớp Học kỳ 1 - Khóa K57 Kinh tế Số",
      targetAmountEth: "0.01",
      deadline: "23:59 ngày 15/11/2026",
      classSize: 5,
      purpose: "Kinh phí phục vụ tài liệu học tập, các buổi sinh hoạt chuyên đề ngoại khóa và quỹ dự phòng hỗ trợ sinh viên K57.",
      status: "Đang diễn ra"
    };

    function getDynamicClassSize(ann) {
      if (classRoster && classRoster.length > 0) return classRoster.length;
      if (ann && ann.classSize) return Number(ann.classSize);
      return 5;
    }

    function getAnnouncementData() {
      try {
        const saved = localStorage.getItem("kts_class_announcement");
        if (saved) {
          const parsed = JSON.parse(saved);
          if (classRoster && classRoster.length > 0) {
            parsed.classSize = classRoster.length;
          }
          return parsed;
        }
      } catch (e) { }
      const def = { ...DEFAULT_ANNOUNCEMENT };
      if (classRoster && classRoster.length > 0) {
        def.classSize = classRoster.length;
      }
      return def;
    }

    function saveAnnouncementData(data) {
      try {
        if (classRoster && classRoster.length > 0) {
          data.classSize = classRoster.length;
        }
        localStorage.setItem("kts_class_announcement", JSON.stringify(data));
      } catch (e) { }
    }

    function renderAnnouncementUI() {
      const ann = getAnnouncementData();
      const currentClassSize = getDynamicClassSize(ann);
      const titleEl = document.getElementById("annTitle");
      const purposeEl = document.getElementById("annPurpose");
      const amountEl = document.getElementById("annAmount");
      const deadlineEl = document.getElementById("annDeadline");
      const classSizeEl = document.getElementById("annClassSize");
      const statusTextEl = document.getElementById("annStatusText");
      const btnDeposit = document.getElementById("btnBannerQuickDeposit");

      if (titleEl) titleEl.textContent = ann.title || DEFAULT_ANNOUNCEMENT.title;
      if (purposeEl) purposeEl.textContent = ann.purpose || DEFAULT_ANNOUNCEMENT.purpose;
      if (amountEl) amountEl.textContent = `${ann.targetAmountEth || "0.01"} ETH / bạn`;
      if (deadlineEl) deadlineEl.textContent = ann.deadline || DEFAULT_ANNOUNCEMENT.deadline;
      if (classSizeEl) classSizeEl.textContent = `${currentClassSize} sinh viên`;
      if (statusTextEl) statusTextEl.textContent = ann.status || "Đang diễn ra";
      if (btnDeposit) btnDeposit.textContent = `⚡ Nộp quỹ ngay (${ann.targetAmountEth || "0.01"} ETH)`;

      // Cập nhật tiến độ
      const depNumText = document.getElementById("metricDepositorsCount")?.textContent || "0";
      const depCount = parseInt(depNumText) || 0;
      updateAnnouncementProgress(depCount);
    }

    function updateAnnouncementProgress(depositorsCount) {
      const ann = getAnnouncementData();
      const count = Number(depositorsCount) || 0;
      const classSize = getDynamicClassSize(ann);
      const percent = classSize > 0 ? Math.min(100, Math.round((count / classSize) * 100)) : 0;

      const progTextEl = document.getElementById("annProgressText");
      const progBarEl = document.getElementById("annProgressBar");

      if (progTextEl) {
        progTextEl.textContent = `${count}/${classSize} bạn đã nộp (${percent}%)`;
      }
      if (progBarEl) {
        progBarEl.style.width = `${percent}%`;
      }
    }

    function openAnnModal() {
      // 1. Kiểm tra kết nối ví
      if (!userAddress) {
        alert(
          "⚠️ Truy cập bị từ chối!\n\n" +
          "Bạn chưa kết nối ví MetaMask. Chức năng chỉnh sửa thông báo CHỈ DÀNH RIÊNG cho tài khoản đăng nhập là Ban cán sự lớp K57.\n\n" +
          "Vui lòng bấm 'Kết nối ví' bằng tài khoản Ban cán sự để tiếp tục."
        );
        return;
      }

      // 2. Kiểm tra phân quyền on-chain nghiêm ngặt: Tuyệt đối không mở cho sinh viên hay chế độ demo
      if (!isBcsMember && !isAdvisor) {
        alert(
          "⚠️ Truy cập bị từ chối!\n\n" +
          `Tài khoản hiện tại (${shortenAddress(userAddress)}) là Sinh viên / Người dùng thông thường, KHÔNG PHẢI Ban cán sự.\n\n` +
          "Theo quy chế quản trị quỹ lớp, sinh viên chỉ có quyền xem thông báo và nộp quỹ, tuyệt đối KHÔNG có quyền chỉnh sửa thông báo của lớp (hệ thống không hỗ trợ chế độ demo)."
        );
        return;
      }

      const ann = getAnnouncementData();
      const currentClassSize = getDynamicClassSize(ann);
      document.getElementById("formAnnTitle").value = ann.title || "";
      document.getElementById("formAnnAmount").value = ann.targetAmountEth || "0.01";
      document.getElementById("formAnnClassSize").value = currentClassSize;
      document.getElementById("formAnnDeadline").value = ann.deadline || "";
      document.getElementById("formAnnPurpose").value = ann.purpose || "";
      document.getElementById("formAnnStatus").value = ann.status || "Đang diễn ra";

      const modalEl = document.getElementById("announcementModal");
      if (modalEl) {
        modalEl.classList.add("open");
        modalEl.classList.add("show");
      }
    }

    function closeAnnModal() {
      const modalEl = document.getElementById("announcementModal");
      if (modalEl) {
        modalEl.classList.remove("open");
        modalEl.classList.remove("show");
      }
    }

    async function syncAnnouncementFromServer() {
      try {
        const resp = await fetch(`${AI_BACKEND_URL}/api/announcement`);
        if (resp.ok) {
          const res = await resp.json();
          if (res.success && res.announcement) {
            saveAnnouncementData(res.announcement);
            renderAnnouncementUI();
            logToTerminal(`[Đồng bộ] Đã tải thông báo mới nhất của lớp từ máy chủ.`);
          }
        }
      } catch (e) {
        console.warn("Chưa thể đồng bộ thông báo từ server, dùng cache offline:", e);
      }
    }

    function initAnnouncementSystem() {
      renderAnnouncementUI();
      syncAnnouncementFromServer();

      // Nút mở modal chỉnh sửa
      const btnOpen = document.getElementById("btnOpenAnnModal");
      if (btnOpen) {
        btnOpen.addEventListener("click", openAnnModal);
      }

      // Nút lưu thông báo trong modal
      const btnSave = document.getElementById("btnSaveAnnouncementModal");
      if (btnSave) {
        btnSave.addEventListener("click", () => {
          // Kiểm tra xác thực quyền hạn trước khi lưu
          if (!userAddress || (!isBcsMember && !isAdvisor)) {
            alert("⚠️ Truy cập bị từ chối: Chỉ tài khoản Ban cán sự mới có quyền lưu và phát thông báo!");
            closeAnnModal();
            return;
          }

          const title = document.getElementById("formAnnTitle").value.trim();
          const amount = document.getElementById("formAnnAmount").value.trim();
          const classSize = getDynamicClassSize(getAnnouncementData());
          const deadline = document.getElementById("formAnnDeadline").value.trim();
          const purpose = document.getElementById("formAnnPurpose").value.trim();
          const status = document.getElementById("formAnnStatus").value;

          if (!title || !amount) {
            alert("Vui lòng nhập đầy đủ tiêu đề và mức nộp!");
            return;
          }

          const newAnn = {
            title,
            targetAmountEth: amount,
            classSize,
            deadline: deadline || "Chưa xác định",
            purpose: purpose || "Kinh phí phục vụ hoạt động lớp",
            status
          };

          saveAnnouncementData(newAnn);
          renderAnnouncementUI();
          closeAnnModal();
          logToTerminal(`[Thông báo] Ban cán sự/Cố vấn đã cập nhật thông báo đợt thu: "${title}" (Mức đóng: ${amount} ETH).`);

          // Đồng bộ lên máy chủ trung tâm (Multi-device Sync)
          fetch(`${AI_BACKEND_URL}/api/announcement`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              ...newAnn,
              signerAddress: userAddress || "Ban cán sự",
              isBcsMember: isBcsMember || (myStudentProfile && myStudentProfile.role === "bcs"),
              isAdvisor: isAdvisor,
              updatedAt: new Date().toISOString()
            })
          })
            .then(res => res.json())
            .then(data => {
              if (data.success) {
                logToTerminal(`[Đồng bộ] Thông báo mới đã được phát tán thành công đến tất cả thiết bị của lớp!`);
                alert("✅ Đã lưu và phát thông báo mới tới toàn thể lớp K57!");
              }
            })
            .catch(err => {
              console.warn("Lỗi đồng bộ server:", err);
            });
        });
      }

      // Nút nộp quỹ nhanh từ Banner
      const btnQuickDep = document.getElementById("btnBannerQuickDeposit");
      if (btnQuickDep) {
        btnQuickDep.addEventListener("click", () => {
          selectRoleView("student");
          const ann = getAnnouncementData();
          const depInput = document.getElementById("inputDepositAmount");
          if (depInput) {
            depInput.value = ann.targetAmountEth || "0.01";
            depInput.focus();
          }
          const studentPanel = document.getElementById("panelStudent");
          if (studentPanel) {
            studentPanel.scrollIntoView({ behavior: "smooth", block: "start" });
          }
          logToTerminal(`[Hành động nhanh] Đã điền sẵn số tiền ${ann.targetAmountEth || "0.01"} ETH theo thông báo lớp.`);
        });
      }
    }

    // --- HÀM ĐỒNG BỘ VÀ LƯU VẾT NGƯỜI NỘP QUỸ ---
    function saveKnownDepositor(addr) {
      if (!addr || !ethers.isAddress(addr)) return;
      try {
        const cached = JSON.parse(localStorage.getItem("kts_known_depositors") || "[]");
        if (!cached.includes(addr.toLowerCase())) {
          cached.push(addr.toLowerCase());
          localStorage.setItem("kts_known_depositors", JSON.stringify(cached));
        }
      } catch (e) { }
    }

    async function syncDepositorsData(classFundWei, adminFeeWei) {
      const depNumEl = document.getElementById("metricDepositorsCount");
      const depNoteEl = document.getElementById("metricDepositorsNote");

      let uniqueMap = new Map();
      let totalWei = 0n;

      // 1. Kiểm tra ví hiện tại của người dùng đang kết nối
      if (userAddress && contract) {
        try {
          const myContrib = await contract.studentContributions(userAddress);
          if (myContrib && myContrib > 0n) {
            totalWei += BigInt(myContrib);
            uniqueMap.set(userAddress.toLowerCase(), {
              address: userAddress,
              totalWei: BigInt(myContrib)
            });
            saveKnownDepositor(userAddress);
          }
        } catch (e) { }
      }

      // 2. Tải danh sách ví đã lưu trong localStorage
      try {
        const cached = JSON.parse(localStorage.getItem("kts_known_depositors") || "[]");
        for (const addr of cached) {
          if (ethers.isAddress(addr) && !uniqueMap.has(addr.toLowerCase()) && contract) {
            try {
              const c = await contract.studentContributions(addr);
              if (c && c > 0n) {
                totalWei += BigInt(c);
                uniqueMap.set(addr.toLowerCase(), {
                  address: addr,
                  totalWei: BigInt(c)
                });
              }
            } catch (e) { }
          }
        }
      } catch (e) { }

      // 3. Quét các applicant từ yêu cầu hoàn tiền (sinh viên làm đơn xin hoàn tiền chắc chắn đã từng nộp quỹ)
      if (contract) {
        try {
          const refCount = Number(await contract.refundRequestCount());
          for (let r = 1; r <= refCount; r++) {
            const req = await contract.getRefundRequest(r);
            const applicant = req[1];
            if (applicant && ethers.isAddress(applicant)) {
              saveKnownDepositor(applicant);
              if (!uniqueMap.has(applicant.toLowerCase())) {
                const c = await contract.studentContributions(applicant);
                if (c && c > 0n) {
                  totalWei += BigInt(c);
                  uniqueMap.set(applicant.toLowerCase(), {
                    address: applicant,
                    totalWei: BigInt(c)
                  });
                }
              }
            }
          }
        } catch (e) { }
      }

      // 4. Quét sự kiện FundDeposited chia thành 5 chunks (mỗi chunk 9000 block, quét ngược tối đa ~45.000 block)
      if (contract && provider) {
        try {
          const currentBlock = await provider.getBlockNumber();
          let toBlock = currentBlock;
          const filter = contract.filters.FundDeposited();
          for (let chunk = 0; chunk < 5; chunk++) {
            if (toBlock <= 0) break;
            const fromBlock = Math.max(0, toBlock - 9000);
            try {
              const events = await contract.queryFilter(filter, fromBlock, toBlock);
              if (events && events.length > 0) {
                events.forEach(ev => {
                  const student = ev.args ? (ev.args[0] || ev.args.student) : null;
                  const amt = ev.args ? (ev.args[1] || ev.args.amount) : 0n;
                  if (student && ethers.isAddress(student)) {
                    saveKnownDepositor(student);
                    const addrLower = student.toLowerCase();
                    if (!uniqueMap.has(addrLower)) {
                      uniqueMap.set(addrLower, {
                        address: student,
                        totalWei: BigInt(amt)
                      });
                    }
                  }
                });
              }
            } catch (chunkErr) {
              console.warn("Chunk scan queryFilter warning:", chunkErr);
              break;
            }
            toBlock = fromBlock - 1;
          }
        } catch (filterErr) {
          console.warn("RPC queryFilter warning:", filterErr);
        }
      }

      // 5. Kiểm tra các sinh viên trong danh bạ K57
      if (contract && classRoster && classRoster.length > 0) {
        for (const s of classRoster) {
          if (s.wallet && ethers.isAddress(s.wallet) && !uniqueMap.has(s.wallet.toLowerCase())) {
            try {
              const c = await contract.studentContributions(s.wallet);
              if (c && c > 0n) {
                totalWei += BigInt(c);
                uniqueMap.set(s.wallet.toLowerCase(), {
                  address: s.wallet,
                  totalWei: BigInt(c)
                });
              }
            } catch (e) { }
          }
        }
      }

      // 6. Đối chiếu số dư thực tế trên hợp đồng
      const cfWei = classFundWei || 0n;
      const afWei = adminFeeWei || 0n;
      const totalOnchainWei = cfWei + afWei;
      const totalOnchainEth = formatEth(totalOnchainWei);

      let finalCount = uniqueMap.size;
      let finalEth = totalOnchainEth;

      // Nếu quỹ đã có tiền (> 0) mà danh sách rỗng, chắc chắn có ít nhất 1 người nộp
      if (finalCount === 0 && totalOnchainWei > 0n) {
        finalCount = 1;
        uniqueMap.set((userAddress || "0xStudent").toLowerCase(), {
          address: userAddress || "Sinh viên đóng quỹ",
          totalWei: totalOnchainWei
        });
      }

      // Cập nhật lên Dashboard
      if (depNumEl) depNumEl.textContent = `${finalCount} sinh viên`;
      if (depNoteEl) depNoteEl.textContent = `Tổng nộp: ${finalEth} ETH`;

      // Cập nhật thanh tiến độ trên Bảng thông báo lớp
      updateAnnouncementProgress(finalCount);

      const canViewIdentity = isAdvisor || isBcsMember;
      const list = Array.from(uniqueMap.values()).map(item => {
        const student = canViewIdentity ? lookupStudent(item.address) : null;
        return {
          address: student ? `${student.name} (${student.mssv})` : shortenAddress(item.address),
          fullAddress: item.address,
          name: student ? student.name : "",
          mssv: student ? student.mssv : "",
          amountEth: formatEth(item.totalWei)
        };
      });

      return {
        count: finalCount,
        totalEth: finalEth,
        list: list
      };
    }

    async function getOnchainSnapshot() {
      const isConnected = !!(contract && CONFIG.contractAddress && ethers.isAddress(CONFIG.contractAddress));

      if (isConnected) {
        try {
          await refreshContractData();
        } catch (e) {
          console.warn("Lỗi refresh trước khi hỏi:", e);
        }
      }

      const classFund = document.getElementById("metricClassFund")?.textContent || "0 ETH";
      const adminFee = document.getElementById("metricAdminFee")?.textContent || "0 ETH";
      let spendCount = Number(document.getElementById("metricSpendCount")?.textContent) || 0;
      let refundCount = Number(document.getElementById("metricRefundCount")?.textContent) || 0;
      let activeBcs = 0;

      if (isConnected) {
        try {
          activeBcs = Number(await contract.activeBCSCount());
          spendCount = Number(await contract.spendRequestCount());
          refundCount = Number(await contract.refundRequestCount());
        } catch (e) {
          console.warn("Lỗi đọc số liệu on-chain:", e);
        }
      }

      // 1. Đồng bộ người nộp quỹ
      let depData = { count: 0, totalEth: "0", list: [] };
      if (isConnected) {
        try {
          const cfWei = await contract.classFundBalance();
          const afWei = await contract.adminFeePool();
          depData = await syncDepositorsData(cfWei, afWei);
        } catch (e) {
          console.warn("Lỗi sync depositors:", e);
        }
      }

      // 2. Đọc trực tiếp danh sách yêu cầu chi và KHỬ TRÙNG LẶP (Deduplicate)
      const spendMap = new Map();
      if (isConnected && spendCount > 0) {
        for (let i = 1; i <= spendCount; i++) {
          try {
            const req = await contract.getSpendRequest(i);
            const reqId = Number(req[0]);
            const recipient = req[1];
            const rawAmount = req[2];
            const desc = req[3];
            const creator = req[4];
            const yesVotes = Number(req[6]);
            const status = Number(req[8]);

            let statusClean = "Đang chờ biểu quyết (Pending)";
            if (status === 1) statusClean = "Đã đủ điều kiện giải ngân (Ready - Đạt >= 51% phiếu thuận)";
            else if (status === 2) statusClean = "Đã thực thi giải ngân thành công (Executed)";
            else if (status === 3 || status === 4) statusClean = "Đã hết hạn hoặc bị hủy (Expired)";

            const bcsNum = activeBcs > 0 ? activeBcs : 1;
            const pct = ((yesVotes / bcsNum) * 100).toFixed(0);

            spendMap.set(reqId, {
              id: reqId,
              description: desc || "Chi hoạt động lớp",
              amountEth: formatEth(rawAmount),
              recipient: shortenAddress(recipient),
              fullRecipient: recipient,
              creator: shortenAddress(creator),
              statusText: statusClean,
              votesText: `${yesVotes}/${bcsNum} phiếu (${pct}%)`
            });
          } catch (err) {
            console.warn("Lỗi đọc yêu cầu chi on-chain:", i, err);
          }
        }
      }

      // 3. Đọc trực tiếp danh sách hoàn tiền và KHỬ TRÙNG LẶP
      const refundMap = new Map();
      if (isConnected && refundCount > 0) {
        for (let i = 1; i <= refundCount; i++) {
          try {
            const req = await contract.getRefundRequest(i);
            const refId = Number(req[0]);
            const applicant = req[1];
            const rawAmount = req[2];
            const reason = req[3];
            const yesVotes = Number(req[5]);
            const status = Number(req[7]);

            let statusClean = "Đang chờ biểu quyết (Pending)";
            if (status === 1) statusClean = "Đã duyệt hoàn tiền (Approved)";
            else if (status === 2) statusClean = "Đã hoàn tiền về ví (Refunded)";
            else if (status === 3) statusClean = "Bị từ chối hoặc hết hạn (Rejected/Expired)";

            refundMap.set(refId, {
              id: refId,
              reason: reason || "Nộp nhầm tiền",
              amountEth: formatEth(rawAmount),
              applicant: shortenAddress(applicant),
              fullApplicant: applicant,
              statusText: statusClean
            });
          } catch (err) {
            console.warn("Lỗi đọc yêu cầu hoàn tiền on-chain:", i, err);
          }
        }
      }

      // 4. Lấy dữ liệu thông báo lớp hiện tại để cấp cho AI
      const ann = getAnnouncementData();
      const depCount = depData.count || 0;
      const classSize = getDynamicClassSize(ann);
      const percent = classSize > 0 ? Math.min(100, Math.round((depCount / classSize) * 100)) : 0;
      const annSnapshot = {
        title: ann.title,
        targetAmountEth: ann.targetAmountEth,
        deadline: ann.deadline,
        classSize: classSize,
        purpose: ann.purpose,
        status: ann.status,
        progressText: `${depCount}/${classSize} bạn đã nộp (${percent}%)`
      };

      // 5. BẢO MẬT & QUYỀN RIÊNG TƯ CHATBOT:
      // Sinh viên & khách vãng lai chỉ được thấy địa chỉ ví on-chain, TUYỆT ĐỐI không gửi danh bạ họ tên/MSSV
      const canViewIdentity = isAdvisor || isBcsMember;
      const safeRoster = canViewIdentity ? classRoster : [];

      return {
        isContractConnected: isConnected,
        contractAddress: CONFIG.contractAddress || "Chưa kết nối",
        userAddress: userAddress || "",
        isBcsMember: isBcsMember || false,
        isAdvisor: isAdvisor || false,
        viewerRole: isAdvisor ? "advisor" : (isBcsMember ? "bcs" : "student"),
        classFundBalanceEth: classFund.replace(" ETH", "").trim(),
        adminFeePoolEth: adminFee.replace(" ETH", "").trim(),
        spendCount: spendCount,
        refundCount: refundCount,
        activeBCSCount: activeBcs,
        depositorsCount: depData.count,
        totalDepositedEth: depData.totalEth,
        depositorsList: depData.list.map(d => ({
          address: canViewIdentity ? d.address : shortenAddress(d.fullAddress || d.address),
          fullAddress: d.fullAddress || d.address,
          name: canViewIdentity ? (d.name || "") : "",
          mssv: canViewIdentity ? (d.mssv || "") : "",
          amountEth: d.amountEth
        })),
        announcement: annSnapshot,
        roster: safeRoster,
        spendRequests: Array.from(spendMap.values()),
        refundRequests: Array.from(refundMap.values())
      };
    }

    async function handleUserSend() {
      const input = document.getElementById("aiUserInput");
      if (!input) return;
      const question = input.value.trim();
      if (!question) return;

      appendAIMessage("user", escapeHtml(question));
      input.value = "";

      const typing = showTypingIndicator();

      try {
        const onchainData = await getOnchainSnapshot();
        const resp = await fetch(`${AI_BACKEND_URL}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question: question,
            signerAddress: userAddress || "",
            isBcsMember: isBcsMember || false,
            isAdvisor: isAdvisor || false,
            onchain_data: onchainData
          })
        });

        removeTypingIndicator();

        if (!resp.ok) {
          const errData = await resp.json().catch(() => ({}));
          const errMsg = errData.error || `Lỗi máy chủ (${resp.status})`;
          appendAIMessage("bot", `⚠️ <strong>Lỗi:</strong> ${escapeHtml(errMsg)}<br><small style="color:var(--text-muted); display:inline-block; margin-top:4px;">💡 Hãy khởi động Backend: <code>python backend/server.py</code> và cấu hình <code>GEMINI_API_KEY</code> trong <code>.env</code>.</small>`);
          return;
        }

        const data = await resp.json();
        if (data.success && data.reply) {
          appendAIMessage("bot", formatAIReply(data.reply));
        } else {
          appendAIMessage("bot", `⚠️ <strong>Lỗi:</strong> ${escapeHtml(data.error || "Không có phản hồi từ AI.")}`);
        }
      } catch (err) {
        removeTypingIndicator();
        appendAIMessage("bot", `⚠️ <strong>Không thể kết nối đến Backend AI:</strong><br>${escapeHtml(err.message)}<br><br><span style="font-size:0.8rem; color:var(--text-muted);">💡 Vui lòng mở terminal và khởi chạy máy chủ:<br><code style="background:#e2e8f0; padding:2px 6px; border-radius:4px; font-weight:600;">python backend/server.py</code></span>`);
      }
    }
  