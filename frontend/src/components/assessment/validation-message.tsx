export function ValidationMessage({ message }: { message: string }) {
  if (!message) return null;
  return <p role="alert" className="mt-4 border-l-2 border-[#b84b3f] bg-[#fff5f3] px-4 py-3 text-lg font-medium leading-8 text-[#8b352d]">{message}</p>;
}