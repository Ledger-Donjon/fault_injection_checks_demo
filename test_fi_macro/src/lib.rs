extern crate proc_macro;
use proc_macro::TokenStream;
use quote::quote;

#[proc_macro_attribute]
pub fn test_fi(_attr: TokenStream, item: TokenStream) -> TokenStream {
    let input = syn::parse_macro_input!(item as syn::ItemFn);
    let name = format!("fi_test_{}", &input.sig.ident);
    let func = &input;

    quote! {
        #[export_name = #name]
        #[inline(never)]
        #func
    }
    .into()
}
