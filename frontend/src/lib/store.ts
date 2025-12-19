import { atom } from 'nanostores';

export type NotificationType = 'success' | 'error' | 'info' | 'warning';

export interface Notification {
    id: string;
    message: string;
    type: NotificationType;
}

export const notifications = atom<Notification[]>([]);

export function addNotification(message: string, type: NotificationType = 'info') {
    const id = crypto.randomUUID();
    const notification: Notification = { id, message, type };

    notifications.set([...notifications.get(), notification]);

    // Auto-dismiss after 3 seconds
    setTimeout(() => {
        removeNotification(id);
    }, 3000);
}

export function removeNotification(id: string) {
    notifications.set(notifications.get().filter(n => n.id !== id));
}
