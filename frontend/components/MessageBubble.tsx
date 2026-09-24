'use client';

import { motion } from 'framer-motion';
import type { ChatMessage } from '@/app/types';

interface Props {
  message: ChatMessage;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user';

  return (
    <div className={`msg-row ${isUser ? 'msg-row--user' : ''}`}>
      <motion.div
        initial={{ opacity: 0, y: 14, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.32, ease: 'easeOut' }}
        className={`bubble ${isUser ? 'bubble--me' : 'bubble--ai'}`}
      >
        {message.content}
      </motion.div>
    </div>
  );
}
