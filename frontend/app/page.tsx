"use client";

import { useEffect, useRef, useState } from "react";

type Message = {
  role: "user" | "assistant";
  content?: string;
  data?: SearchResult;
};

type VendorResult = {
  vendor_id: number;
  vendor: string;
  contact: string;
  mail_id: string;
};

type ProductResult = {
  product_id: number;
  product_name: string;
};

type MatchResult = {
  product_id?: number;
  product_name?: string;
  vendor_id?: number;
  vendor_name?: string;
  score?: number;
};

type SearchResult = {
  type: string;
  matched_name?: string;
  results?: VendorResult[] | ProductResult[] | MatchResult[];
  vendor_details?: {
    vendor?: string;
    contact?: string;
    mail_id?: string;
  };
  message?: string;
};

type SuggestionProduct = {
  product_id: number;
  product_name: string;
};

type SuggestionVendor = {
  vendor_id: number;
  vendor_name: string;
};

type Suggestions = {
  products: SuggestionProduct[];
  vendors: SuggestionVendor[];
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // Autocomplete state
  const [suggestions, setSuggestions] =
    useState<Suggestions>({
      products: [],
      vendors: [],
    });

  const [showSuggestions, setShowSuggestions] =
    useState(false);

  const [suggestionLoading, setSuggestionLoading] =
    useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputContainerRef =
    useRef<HTMLDivElement>(null);

  // =========================================================
  // AUTO SCROLL
  // =========================================================

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, loading]);

  // =========================================================
  // FETCH AUTOCOMPLETE SUGGESTIONS
  // =========================================================

  useEffect(() => {
    const query = input.trim();

    if (!query) {
      setSuggestions({
        products: [],
        vendors: [],
      });

      setShowSuggestions(false);

      return;
    }

    // Don't show suggestions while searching
    if (loading) {
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setSuggestionLoading(true);

        const response = await fetch(
          `http://localhost:8000/api/suggestions?q=${encodeURIComponent(
            query
          )}`
        );

        if (!response.ok) {
          throw new Error(
            "Suggestion request failed"
          );
        }

        const data: Suggestions =
          await response.json();

        setSuggestions(data);

        const hasSuggestions =
          data.products.length > 0 ||
          data.vendors.length > 0;

        setShowSuggestions(hasSuggestions);
      } catch (error) {
        console.error(
          "Suggestion error:",
          error
        );

        setSuggestions({
          products: [],
          vendors: [],
        });

        setShowSuggestions(false);
      } finally {
        setSuggestionLoading(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [input, loading]);

  // =========================================================
  // CLOSE SUGGESTIONS WHEN CLICKING OUTSIDE
  // =========================================================

  useEffect(() => {
    const handleOutsideClick = (
      event: MouseEvent
    ) => {
      if (
        inputContainerRef.current &&
        !inputContainerRef.current.contains(
          event.target as Node
        )
      ) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener(
      "mousedown",
      handleOutsideClick
    );

    return () => {
      document.removeEventListener(
        "mousedown",
        handleOutsideClick
      );
    };
  }, []);

  // =========================================================
  // SEARCH FUNCTION
  // =========================================================

  const searchQuery = async (query: string) => {
    const trimmedQuery = query.trim();

    if (!trimmedQuery || loading) {
      return;
    }

    setShowSuggestions(false);

    setMessages((previous) => [
      ...previous,
      {
        role: "user",
        content: trimmedQuery,
      },
    ]);

    setInput("");
    setLoading(true);

    try {
      const response = await fetch(
        "http://localhost:8000/api/search",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            query: trimmedQuery,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(
          "Search request failed"
        );
      }

      const data: SearchResult =
        await response.json();

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          data,
        },
      ]);
    } catch (error) {
      console.error(error);

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content:
            "Unable to connect to the search server. Please make sure the FastAPI backend is running.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // =========================================================
  // SEND MESSAGE
  // =========================================================

  const sendMessage = async () => {
    await searchQuery(input);
  };

  // =========================================================
  // ENTER KEY
  // =========================================================

  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLInputElement>
  ) => {
    if (event.key === "Enter") {
      event.preventDefault();

      setShowSuggestions(false);

      sendMessage();
    }

    if (event.key === "Escape") {
      setShowSuggestions(false);
    }
  };

  // =========================================================
  // CLEAR CHAT
  // =========================================================

  const clearChat = () => {
    setMessages([]);
    setInput("");
    setSuggestions({
      products: [],
      vendors: [],
    });
    setShowSuggestions(false);
  };

  // =========================================================
  // QUICK SEARCH
  // =========================================================

  const quickSearch = (value: string) => {
    setInput(value);

    setTimeout(() => {
      const inputElement =
        document.querySelector(
          'input[placeholder="Search product or vendor..."]'
        ) as HTMLInputElement | null;

      inputElement?.focus();
    }, 0);
  };

  // =========================================================
  // CLICKABLE SEARCH
  // =========================================================

  const clickableSearch = async (
    value: string
  ) => {
    if (loading) {
      return;
    }

    await searchQuery(value);
  };

  // =========================================================
  // SELECT AUTOCOMPLETE SUGGESTION
  // =========================================================

  const selectSuggestion = async (
    value: string
  ) => {
    setShowSuggestions(false);
    setSuggestions({
      products: [],
      vendors: [],
    });

    await searchQuery(value);
  };

  // =========================================================
  // RENDER RESULT
  // =========================================================

  const renderResult = (
    data: SearchResult
  ) => {
    // =======================================================
    // PRODUCT RESULT
    // =======================================================

    if (data.type === "product") {
      const vendors =
        (data.results || []) as VendorResult[];

      return (
        <div className="space-y-5">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-xl">
              📦
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
                Product
              </p>

              <h2 className="mt-1 text-xl font-semibold text-gray-900">
                {data.matched_name}
              </h2>
            </div>
          </div>

          <div>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-800">
                Associated Vendors
              </h3>

              <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
                {vendors.length}{" "}
                {vendors.length === 1
                  ? "Vendor"
                  : "Vendors"}
              </span>
            </div>

            {vendors.length === 0 ? (
              <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-5 text-sm text-gray-500">
                No vendors are associated with this
                product.
              </div>
            ) : (
              <div className="overflow-hidden rounded-xl border border-gray-200">
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[650px] text-left">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="w-16 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
                          #
                        </th>

                        <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
                          Vendor
                        </th>

                        <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
                          Contact
                        </th>

                        <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
                          Mail ID
                        </th>
                      </tr>
                    </thead>

                    <tbody className="divide-y divide-gray-100 bg-white">
                      {vendors.map(
                        (vendor, index) => (
                          <tr
                            key={`${vendor.vendor_id}-${index}`}
                            className="transition hover:bg-gray-50"
                          >
                            <td className="px-4 py-4 text-sm text-gray-400">
                              {index + 1}
                            </td>

                            <td className="px-4 py-4">
                              <button
                                onClick={() =>
                                  clickableSearch(
                                    vendor.vendor
                                  )
                                }
                                disabled={loading}
                                className="text-left font-medium text-blue-600 transition hover:text-blue-800 hover:underline disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                {vendor.vendor}
                              </button>
                            </td>

                            <td className="px-4 py-4 text-sm text-gray-600">
                              {vendor.contact ? (
                                <a
                                  href={`tel:${vendor.contact}`}
                                  className="hover:text-blue-600 hover:underline"
                                >
                                  {vendor.contact}
                                </a>
                              ) : (
                                <span className="text-gray-300">
                                  —
                                </span>
                              )}
                            </td>

                            <td className="px-4 py-4 text-sm text-gray-600">
                              {vendor.mail_id ? (
                                <a
                                  href={`mailto:${vendor.mail_id}`}
                                  className="hover:text-blue-600 hover:underline"
                                >
                                  {vendor.mail_id}
                                </a>
                              ) : (
                                <span className="text-gray-300">
                                  —
                                </span>
                              )}
                            </td>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      );
    }

    // =======================================================
    // VENDOR RESULT
    // =======================================================

    if (data.type === "vendor") {
      const products =
        (data.results || []) as ProductResult[];

      const contact =
        data.vendor_details?.contact || "";

      const mailId =
        data.vendor_details?.mail_id || "";

      return (
        <div className="space-y-5">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-xl">
              🏢
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
                Vendor
              </p>

              <h2 className="mt-1 text-xl font-semibold text-gray-900">
                {data.matched_name}
              </h2>
            </div>
          </div>

          <div>
            <h3 className="mb-3 text-sm font-semibold text-gray-800">
              Contact Details
            </h3>

            <div className="grid gap-3 sm:grid-cols-2">
              {contact && (
                <a
                  href={`tel:${contact}`}
                  className="group rounded-xl border border-gray-200 bg-gray-50 p-4 transition hover:border-gray-300 hover:bg-white"
                >
                  <div className="mb-1 text-xs font-medium uppercase tracking-wide text-gray-400">
                    Contact
                  </div>

                  <div className="font-medium text-gray-800 group-hover:text-blue-600">
                    {contact}
                  </div>
                </a>
              )}

              {mailId && (
                <a
                  href={`mailto:${mailId}`}
                  className="group rounded-xl border border-gray-200 bg-gray-50 p-4 transition hover:border-gray-300 hover:bg-white"
                >
                  <div className="mb-1 text-xs font-medium uppercase tracking-wide text-gray-400">
                    Mail ID
                  </div>

                  <div className="break-all font-medium text-gray-800 group-hover:text-blue-600">
                    {mailId}
                  </div>
                </a>
              )}

              {!contact && !mailId && (
                <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-4 text-sm text-gray-500 sm:col-span-2">
                  No contact information is available
                  for this vendor.
                </div>
              )}
            </div>
          </div>

          <div>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-800">
                Associated Products
              </h3>

              <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
                {products.length}{" "}
                {products.length === 1
                  ? "Product"
                  : "Products"}
              </span>
            </div>

            {products.length === 0 ? (
              <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-5 text-sm text-gray-500">
                No products are associated with this
                vendor.
              </div>
            ) : (
              <div className="overflow-hidden rounded-xl border border-gray-200">
                <table className="w-full text-left">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="w-16 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
                        #
                      </th>

                      <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
                        Product
                      </th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-gray-100 bg-white">
                    {products.map(
                      (product, index) => (
                        <tr
                          key={`${product.product_id}-${index}`}
                          className="transition hover:bg-gray-50"
                        >
                          <td className="px-4 py-4 text-sm text-gray-400">
                            {index + 1}
                          </td>

                          <td className="px-4 py-4">
                            <button
                              onClick={() =>
                                clickableSearch(
                                  product.product_name
                                )
                              }
                              disabled={loading}
                              className="text-left font-medium text-blue-600 transition hover:text-blue-800 hover:underline disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              {product.product_name}
                            </button>
                          </td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      );
    }

    // =======================================================
    // MULTIPLE PRODUCTS
    // =======================================================

    if (data.type === "multiple_products") {
      const matches =
        (data.results || []) as MatchResult[];

      return (
        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-xl">
              🔎
            </div>

            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Multiple Products Found
              </h2>

              <p className="mt-1 text-sm text-gray-500">
                Click a product below to search it.
              </p>
            </div>
          </div>

          <div className="overflow-hidden rounded-xl border border-gray-200">
            <table className="w-full text-left">
              <thead className="bg-gray-50">
                <tr>
                  <th className="w-16 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
                    #
                  </th>

                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Product
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-gray-100 bg-white">
                {matches.map((item, index) => (
                  <tr
                    key={`${item.product_id}-${index}`}
                    className="transition hover:bg-gray-50"
                  >
                    <td className="px-4 py-4 text-sm text-gray-400">
                      {index + 1}
                    </td>

                    <td className="px-4 py-4">
                      <button
                        onClick={() =>
                          clickableSearch(
                            item.product_name || ""
                          )
                        }
                        disabled={loading}
                        className="font-medium text-blue-600 hover:text-blue-800 hover:underline disabled:opacity-50"
                      >
                        {item.product_name}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      );
    }

    // =======================================================
    // MULTIPLE VENDORS
    // =======================================================

    if (data.type === "multiple_vendors") {
      const matches =
        (data.results || []) as MatchResult[];

      return (
        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-xl">
              🔎
            </div>

            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Multiple Vendors Found
              </h2>

              <p className="mt-1 text-sm text-gray-500">
                Click a vendor below to search it.
              </p>
            </div>
          </div>

          <div className="overflow-hidden rounded-xl border border-gray-200">
            <table className="w-full text-left">
              <thead className="bg-gray-50">
                <tr>
                  <th className="w-16 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
                    #
                  </th>

                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Vendor
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-gray-100 bg-white">
                {matches.map((item, index) => (
                  <tr
                    key={`${item.vendor_id}-${index}`}
                    className="transition hover:bg-gray-50"
                  >
                    <td className="px-4 py-4 text-sm text-gray-400">
                      {index + 1}
                    </td>

                    <td className="px-4 py-4">
                      <button
                        onClick={() =>
                          clickableSearch(
                            item.vendor_name || ""
                          )
                        }
                        disabled={loading}
                        className="font-medium text-blue-600 hover:text-blue-800 hover:underline disabled:opacity-50"
                      >
                        {item.vendor_name}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      );
    }

    // =======================================================
    // NO MATCH
    // =======================================================

    return (
      <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
        <span className="text-xl">🔎</span>

        <div>
          <p className="font-medium text-gray-800">
            No matching product or vendor found
          </p>

          <p className="mt-1 text-sm text-gray-600">
            Try checking the spelling or searching with a
            different name.
          </p>
        </div>
      </div>
    );
  };

  // =========================================================
  // MAIN UI
  // =========================================================

  return (
    <main className="min-h-screen bg-[#f7f7f8]">
      {/* ===================================================
          HEADER
      =================================================== */}

      <header className="sticky top-0 z-20 border-b border-gray-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-black text-lg text-white">
              🔎
            </div>

            <div>
              <h1 className="text-sm font-semibold text-gray-900 sm:text-base">
                Vendor–Product Search
              </h1>

              <p className="hidden text-xs text-gray-500 sm:block">
                Search vendors and products
              </p>
            </div>
          </div>

          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="rounded-lg px-3 py-2 text-xs font-medium text-gray-500 transition hover:bg-gray-100 hover:text-gray-900"
            >
              New Search
            </button>
          )}
        </div>
      </header>

      {/* ===================================================
          CHAT AREA
      =================================================== */}

      <div className="mx-auto flex min-h-[calc(100vh-64px)] max-w-4xl flex-col">
        <section className="flex-1 px-4 py-6 sm:px-6 sm:py-8">
          {/* EMPTY STATE */}

          {messages.length === 0 && (
            <div className="flex min-h-[65vh] flex-col items-center justify-center text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-black text-3xl shadow-sm">
                🔎
              </div>

              <h2 className="mt-6 text-2xl font-semibold tracking-tight text-gray-900 sm:text-3xl">
                Vendor–Product Search
              </h2>

              <p className="mt-3 max-w-lg text-sm leading-6 text-gray-500 sm:text-base">
                Search for a product to find its associated
                vendors, or search for a vendor to find its
                associated products.
              </p>

              <div className="mt-8 grid w-full max-w-xl gap-3 sm:grid-cols-2">
                <button
                  onClick={() =>
                    quickSearch("PHENOL")
                  }
                  className="rounded-xl border border-gray-200 bg-white p-4 text-left transition hover:border-gray-300 hover:shadow-sm"
                >
                  <div className="text-sm font-medium text-gray-900">
                    📦 Search a product
                  </div>

                  <div className="mt-1 text-xs text-gray-500">
                    Example: PHENOL
                  </div>
                </button>

                <button
                  onClick={() =>
                    quickSearch(
                      "FLORA CHEMICALS"
                    )
                  }
                  className="rounded-xl border border-gray-200 bg-white p-4 text-left transition hover:border-gray-300 hover:shadow-sm"
                >
                  <div className="text-sm font-medium text-gray-900">
                    🏢 Search a vendor
                  </div>

                  <div className="mt-1 text-xs text-gray-500">
                    Example: FLORA CHEMICALS
                  </div>
                </button>
              </div>
            </div>
          )}

          {/* CHAT MESSAGES */}

          <div className="space-y-8">
            {messages.map(
              (message, index) => {
                if (message.role === "user") {
                  return (
                    <div
                      key={index}
                      className="flex justify-end"
                    >
                      <div className="max-w-[85%] rounded-2xl rounded-br-md bg-black px-5 py-3.5 text-sm leading-6 text-white shadow-sm">
                        {message.content}
                      </div>
                    </div>
                  );
                }

                return (
                  <div
                    key={index}
                    className="flex gap-3 sm:gap-4"
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-black text-sm text-white">
                      🔎
                    </div>

                    <div className="min-w-0 flex-1 pt-0.5">
                      {message.data ? (
                        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-6">
                          {renderResult(
                            message.data
                          )}
                        </div>
                      ) : (
                        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm leading-6 text-red-700">
                          {message.content}
                        </div>
                      )}
                    </div>
                  </div>
                );
              }
            )}

            {/* LOADING */}

            {loading && (
              <div className="flex gap-3 sm:gap-4">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-black text-sm text-white">
                  🔎
                </div>

                <div className="rounded-2xl border border-gray-200 bg-white px-5 py-4 shadow-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-500">
                      Searching
                    </span>

                    <span className="flex gap-1">
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.3s]" />

                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.15s]" />

                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400" />
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div ref={messagesEndRef} />
        </section>

        {/* ===================================================
            SEARCH INPUT
        =================================================== */}

        <div className="sticky bottom-0 px-4 pb-5 pt-2 sm:px-6">
          <div
            ref={inputContainerRef}
            className="relative mx-auto max-w-3xl"
          >
            {/* =================================================
                AUTOCOMPLETE DROPDOWN
            ================================================= */}

            {showSuggestions && (
              <div className="absolute bottom-full left-0 right-0 mb-2 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-xl">
                {/* Suggestion loading */}

                {suggestionLoading &&
                  suggestions.products.length === 0 &&
                  suggestions.vendors.length === 0 && (
                    <div className="px-4 py-4 text-sm text-gray-500">
                      Searching suggestions...
                    </div>
                  )}

                {/* Products */}

                {suggestions.products.length >
                  0 && (
                  <div>
                    <div className="border-b border-gray-100 bg-gray-50 px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
                      📦 Products
                    </div>

                    <div className="p-1">
                      {suggestions.products.map(
                        (product) => (
                          <button
                            key={`product-${product.product_id}`}
                            onClick={() =>
                              selectSuggestion(
                                product.product_name
                              )
                            }
                            className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left transition hover:bg-gray-100"
                          >
                            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-50">
                              📦
                            </span>

                            <span className="text-sm font-medium text-gray-800">
                              {product.product_name}
                            </span>
                          </button>
                        )
                      )}
                    </div>
                  </div>
                )}

                {/* Vendors */}

                {suggestions.vendors.length >
                  0 && (
                  <div>
                    <div className="border-y border-gray-100 bg-gray-50 px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
                      🏢 Vendors
                    </div>

                    <div className="p-1">
                      {suggestions.vendors.map(
                        (vendor) => (
                          <button
                            key={`vendor-${vendor.vendor_id}`}
                            onClick={() =>
                              selectSuggestion(
                                vendor.vendor_name
                              )
                            }
                            className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left transition hover:bg-gray-100"
                          >
                            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-50">
                              🏢
                            </span>

                            <span className="text-sm font-medium text-gray-800">
                              {vendor.vendor_name}
                            </span>
                          </button>
                        )
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Search box */}

            <div className="rounded-2xl border border-gray-300 bg-white p-2 shadow-lg shadow-gray-200/50">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(event) =>
                    setInput(
                      event.target.value
                    )
                  }
                  onFocus={() => {
                    if (
                      suggestions.products
                        .length > 0 ||
                      suggestions.vendors
                        .length > 0
                    ) {
                      setShowSuggestions(
                        true
                      );
                    }
                  }}
                  onKeyDown={handleKeyDown}
                  placeholder="Search product or vendor..."
                  disabled={loading}
                  className="min-w-0 flex-1 bg-transparent px-3 py-3 text-sm text-gray-900 outline-none placeholder:text-gray-400"
                />

                {/* Clear input */}

                {input && !loading && (
                  <button
                    onClick={() => {
                      setInput("");
                      setShowSuggestions(false);
                    }}
                    className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-700"
                    aria-label="Clear search"
                  >
                    ×
                  </button>
                )}

                {/* Search button */}

                <button
                  onClick={sendMessage}
                  disabled={
                    loading || !input.trim()
                  }
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-black text-white transition hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-30"
                  aria-label="Search"
                >
                  ↑
                </button>
              </div>
            </div>

            <p className="mt-2 text-center text-[11px] text-gray-400">
              Search results are retrieved from the
              vendor and product database.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
