"use client";

import { useSyncExternalStore } from "react";

const changeEvent = "webintelx-storage-change";

function subscribe(listener: () => void) {
  window.addEventListener("storage", listener);
  window.addEventListener(changeEvent, listener);
  return () => {
    window.removeEventListener("storage", listener);
    window.removeEventListener(changeEvent, listener);
  };
}

export function useBrowserStoredValue<T extends string | number>(
  key: string,
  fallback: T,
  parse: (value: string | null) => T,
) {
  const value = useSyncExternalStore(
    subscribe,
    () => parse(window.localStorage.getItem(key)),
    () => fallback,
  );

  const setValue = (nextValue: T) => {
    try {
      window.localStorage.setItem(key, String(nextValue));
    } catch {
      return;
    }
    window.dispatchEvent(new Event(changeEvent));
  };

  return [value, setValue] as const;
}
