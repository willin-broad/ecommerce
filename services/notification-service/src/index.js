const amqp = require('amqplib');
require('dotenv').config();

const RABBITMQ_URL = process.env.RABBITMQ_URL || 'amqp://localhost';
const QUEUE = 'notifications';

async function startConsumer() {
  const conn = await amqp.connect(RABBITMQ_URL);
  const channel = await conn.createChannel();
  await channel.assertQueue(QUEUE, { durable: true });
  console.log(`notification-service listening on queue: ${QUEUE}`);

  channel.consume(QUEUE, (msg) => {
    if (msg !== null) {
      const payload = JSON.parse(msg.content.toString());
      console.log('[Notification]', payload);
      // TODO: integrate email (nodemailer) or SMS (Twilio)
      channel.ack(msg);
    }
  });
}

startConsumer().catch(console.error);
