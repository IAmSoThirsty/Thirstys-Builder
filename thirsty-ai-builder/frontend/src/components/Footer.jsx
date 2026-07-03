import React from "react";

const OWNER = "Jeremy Karrick / Thirsty's Projects LLC";
const ENTITY = "Entity #14694374-0160";
const OFFICE = "1450 South West Temple Street, A402, Salt Lake City, UT 84115-5203";
const COPYRIGHT = `\u00a9 2026 ${OWNER}. ${ENTITY}. All rights reserved.`;

export default function Footer() {
  return (
    <footer className="border-t border-white/5 mt-12">
      <div className="max-w-[1100px] mx-auto px-6 py-6 text-sm text-brand-200 flex flex-wrap items-center justify-between gap-2">
        <div>{COPYRIGHT}</div>
        <div>{OFFICE}</div>
      </div>
    </footer>
  );
}
