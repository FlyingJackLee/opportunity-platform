export default function DeleteButton({ label, onDelete }: { label: string; onDelete: () => void }) {
  return (
    <button
      onClick={() => {
        if (confirm(`确定要彻底删除「${label}」吗？此操作不可撤销。`)) {
          onDelete();
        }
      }}
    >
      删除
    </button>
  );
}
