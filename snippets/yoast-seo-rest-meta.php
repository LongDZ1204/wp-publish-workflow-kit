<?php
/**
 * Allow authenticated editors to read and write the Yoast SEO title and
 * meta description through the standard WordPress REST API.
 *
 * Install only when Yoast SEO is the site's active SEO plugin.
 */

defined( 'ABSPATH' ) || exit;

add_action(
	'init',
	static function () {
		$keys = array( '_yoast_wpseo_title', '_yoast_wpseo_metadesc' );

		foreach ( array( 'post', 'page' ) as $post_type ) {
			foreach ( $keys as $key ) {
				register_post_meta(
					$post_type,
					$key,
					array(
						'type'              => 'string',
						'single'            => true,
						'show_in_rest'      => true,
						'sanitize_callback' => 'sanitize_text_field',
						'auth_callback'     => static function ( $allowed, $meta_key, $post_id ) {
							return current_user_can( 'edit_post', $post_id );
						},
					)
				);
			}
		}
	}
);
