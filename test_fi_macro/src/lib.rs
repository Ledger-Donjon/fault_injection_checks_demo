extern crate proc_macro;
use proc_macro::TokenStream;
use quote::{quote, format_ident};

#[proc_macro_attribute]
pub fn test_fi(_attr: TokenStream, item: TokenStream) -> TokenStream {
    let mut input = syn::parse_macro_input!(item as syn::ItemFn);
    let name = format!("test_fi_{}", &input.sig.ident);
    let name_nominal_behavior = format_ident!("nominal_behavior_test_fi_{}", &input.sig.ident);

    // Insert nominal_behavior() call at the end
    input.block.stmts.push(syn::parse(quote!(#name_nominal_behavior();).into()).unwrap());

    quote! {
        #[no_mangle]
        #[inline(never)]
        fn #name_nominal_behavior() {
            println!("nominal behavior")
        }

        #[export_name = #name]
        #[inline(never)]
        #input
    }
    .into()
}
