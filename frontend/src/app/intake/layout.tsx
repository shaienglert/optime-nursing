import "./conversation.css";

import { ConversationController } from "./conversation-controller";

export default function IntakeLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="optime-conversation-intake">
      <ConversationController>{children}</ConversationController>
    </div>
  );
}
