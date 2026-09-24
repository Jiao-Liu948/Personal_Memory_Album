'use client';

interface Props {
  text?: string;
}

export default function Typing({ text = '正在回忆...' }: Props) {
  return (
    <div className="msg-row">
      <div className="typing">
        <i />
        <i />
        <i />
        <span style={{ marginLeft: 6 }}>{text}</span>
      </div>
    </div>
  );
}
