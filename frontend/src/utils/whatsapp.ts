/**
 * Utility for 100% Free WhatsApp Bill Invoice sharing via linked WhatsApp account.
 * Works with WhatsApp Desktop or WhatsApp Web without Meta API costs or accounts.
 */

export interface WhatsAppBillItem {
  name: string;
  quantity: number;
  price: number; // or subtotal
  discount?: number;
}

export interface WhatsAppBillData {
  customerName?: string;
  customerPhone?: string;
  invoiceNo: string;
  createdAt?: string;
  paymentMethod?: string;
  items: WhatsAppBillItem[];
  subtotal: number;
  discount?: number;
  tax?: number;
  total: number;
  storeName?: string;
  storePhone?: string;
  storeAddress?: string;
}

export function formatWhatsAppPhone(phone?: string): string {
  if (!phone) return '';
  const digits = phone.replace(/\D/g, '');
  if (digits.length === 10) {
    return `91${digits}`;
  }
  if (digits.length === 12 && digits.startsWith('91')) {
    return digits;
  }
  return digits;
}

export function buildWhatsAppBillText(data: WhatsAppBillData): string {
  const storeName = (data.storeName || 'MOIRA LUXE').toUpperCase();
  const customerName = data.customerName?.trim() || 'Valued Customer';
  const payMode = (data.paymentMethod || 'CASH').toUpperCase();
  const dateStr = data.createdAt || new Date().toLocaleString('en-IN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });

  const lines: string[] = [];
  lines.push(`✨ *${storeName}* ✨`);
  lines.push(`*BILL INVOICE*`);
  lines.push(`--------------------------------`);
  lines.push(`Dear *${customerName}*,`);
  lines.push(`Thank you for shopping with us!`);
  lines.push(``);
  lines.push(`🧾 *Bill No:* ${data.invoiceNo}`);
  lines.push(`📅 *Date:* ${dateStr}`);
  lines.push(`💳 *Payment:* ${payMode}`);
  lines.push(``);
  lines.push(`*Items Purchased:*`);

  data.items.forEach((item) => {
    const qty = item.quantity || 1;
    const name = item.name || 'Item';
    const price = Number(item.price || 0).toFixed(2);
    lines.push(`• ${qty}x ${name} - Rs. ${price}`);
  });

  lines.push(``);
  lines.push(`Subtotal: Rs. ${Number(data.subtotal || 0).toFixed(2)}`);

  if (data.discount && data.discount > 0) {
    lines.push(`Total Discount: -Rs. ${Number(data.discount).toFixed(2)}`);
  }

  if (data.tax && data.tax > 0) {
    lines.push(`GST / Tax: +Rs. ${Number(data.tax).toFixed(2)}`);
  }

  lines.push(`*GRAND TOTAL: Rs. ${Number(data.total || 0).toFixed(2)}*`);
  lines.push(`--------------------------------`);

  // E-Invoice link (public web view)
  const origin = window.location.origin;
  const invoiceLink = `${origin}/api/billing/public-invoice/${encodeURIComponent(data.invoiceNo)}`;
  lines.push(`📄 *View E-Invoice:*`);
  lines.push(invoiceLink);
  lines.push(``);

  if (data.storeAddress || data.storePhone) {
    const storeInfo = [data.storeAddress, data.storePhone ? `Ph: ${data.storePhone}` : ''].filter(Boolean).join(' | ');
    lines.push(`📍 ${storeInfo}`);
  }
  lines.push(`✨ *Have a wonderful day!* ✨`);

  return lines.join('\n');
}

import api from '../api/client';
import toast from 'react-hot-toast';

export function openWhatsAppBill(data: WhatsAppBillData): boolean {
  const cleanPhone = formatWhatsAppPhone(data.customerPhone);
  if (!cleanPhone) {
    return false;
  }

  const message = buildWhatsAppBillText(data);
  const encodedMsg = encodeURIComponent(message);

  // Direct wa.me link seamlessly opens WhatsApp Desktop or WhatsApp Web
  const waUrl = `https://wa.me/${cleanPhone}?text=${encodedMsg}`;
  
  if ((window as any).pywebview?.api?.open_external) {
    (window as any).pywebview.api.open_external(waUrl);
  } else {
    window.open(waUrl, '_blank', 'noopener,noreferrer');
  }
  return true;
}

/**
 * Autonomous delivery first via linked Baileys engine,
 * falling back to wa.me if unlinked.
 */
export async function dispatchWhatsAppBill(data: WhatsAppBillData): Promise<boolean> {
  const cleanPhone = formatWhatsAppPhone(data.customerPhone);
  if (!cleanPhone) {
    return false;
  }

  const message = buildWhatsAppBillText(data);

  // 1. Try autonomous direct delivery via local Baileys engine
  try {
    const res = await api.post('/whatsapp/send', {
      phone: cleanPhone,
      message: message,
    });
    if (res.data?.success) {
      toast.success(`📱 WhatsApp Bill delivered autonomously to +${cleanPhone}!`);
      return true;
    }
  } catch (err) {
    // If Baileys not connected yet or offline, proceed to fallback
  }

  // 2. Seamless fallback: open wa.me
  return openWhatsAppBill(data);
}
